"""Portable copy of the original Codex subscription transport. No project imports."""
import json, os, queue, re, subprocess, tempfile, threading, time, tomllib
from collections import deque
from pathlib import Path
SCHEMA = {}
class CodexServer:

    def __init__(self, work, model, window_limit=8, window_seconds=65):
        self.model = model
        self.temp = tempfile.TemporaryDirectory(prefix='luna-inference-', dir=work)
        self.cwd = str(Path(self.temp.name).resolve())
        self.lock = threading.Lock()
        self.pending = {}
        self.events = {}
        self.seq = 0
        self.rate_lock = threading.Lock()
        self.turn_starts = deque()
        self.window_limit = window_limit
        self.window_seconds = window_seconds
        cmd = ['codex', 'app-server', '--listen', 'stdio://', '-c', 'model_provider="openai"', '-c', 'web_search="disabled"', '-c', 'project_doc_max_bytes=0']
        for flag in ['shell_tool', 'apps', 'plugins', 'multi_agent', 'computer_use', 'browser_use', 'code_mode_host', 'goals', 'skill_search', 'hooks', 'view_image', 'image_generation']:
            cmd += ['--disable', flag]
        cmd += ['--enable', 'skip_host_skill_discovery']
        config = Path(os.getenv('CODEX_HOME', str(Path.home() / '.codex'))) / 'config.toml'
        if config.is_file():
            cfg = tomllib.loads(config.read_text())
            for name in cfg.get('mcp_servers', {}):
                if not re.fullmatch('[A-Za-z0-9_-]+', name):
                    raise ValueError('Cannot safely disable configured MCP server name')
                cmd += ['-c', f'mcp_servers.{name}.enabled=false']
        env = {k: v for k, v in os.environ.items() if not any((x in k.upper() for x in ['MINIMAX', 'NEXT_API', 'NEXT_MODEL', 'NEXT_QUERY_MODEL']))}
        self.process = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=1, cwd=self.cwd, env=env)
        self.diagnostics = []
        threading.Thread(target=self._errors, daemon=True).start()
        self.reader = threading.Thread(target=self._read, daemon=True)
        self.reader.start()
        try:
            self.rpc('initialize', {'clientInfo': {'name': 'next_app_retrieval', 'title': 'next-app retrieval benchmark', 'version': '0.1'}, 'capabilities': {'experimentalApi': True}})
            self.send({'method': 'initialized'})
        except BaseException:
            self.close()
            raise

    def _errors(self):
        for line in self.process.stderr:
            line = re.sub('\\b(?:sk-[\\w.-]+|eyJ[\\w-]+\\.[\\w-]+\\.[\\w-]+)|Bearer\\s+\\S+', '[REDACTED]', line)
            self.diagnostics.append(line.strip()[:400])
            self.diagnostics = self.diagnostics[-4:]

    def send(self, data):
        with self.lock:
            self.process.stdin.write(json.dumps(data, ensure_ascii=False) + '\n')
            self.process.stdin.flush()

    def _read(self):
        for line in self.process.stdout:
            try:
                message = json.loads(line)
            except ValueError:
                continue
            if 'id' in message and 'method' not in message:
                target = self.pending.get(message['id'])
                if target:
                    target.put(message)
            elif 'id' in message:
                self.send({'id': message['id'], 'error': {'code': -32601, 'message': 'Tools and approval requests disabled in retrieval benchmark'}})
            else:
                params = message.get('params', {})
                target = self.events.get(params.get('threadId'))
                if target:
                    target.put(message)
        for target in list(self.pending.values()):
            target.put({'error': {'message': 'Codex process exited before response', 'diagnostic': self.diagnostics}})

    def rpc(self, method, params, timeout=60):
        with self.lock:
            self.seq += 1
            ident = self.seq
            result = queue.Queue()
            self.pending[ident] = result
        self.send({'id': ident, 'method': method, 'params': params})
        try:
            response = result.get(timeout=timeout)
        except queue.Empty:
            raise TimeoutError('Codex app-server RPC timed out: ' + method) from None
        finally:
            self.pending.pop(ident, None)
        if 'error' in response:
            raise RuntimeError('Codex RPC failed: ' + json.dumps(response['error'], ensure_ascii=False))
        return response['result']

    def infer(self, system, payload, effort='none', schema=None):
        started = time.monotonic()
        thread = self.rpc('thread/start', {'model': self.model, 'modelProvider': 'openai', 'cwd': self.cwd, 'ephemeral': True, 'approvalPolicy': 'never', 'sandbox': 'read-only', 'baseInstructions': system + '\n只根据提供的数据作判断。不得调用工具、访问文件或网络。', 'developerInstructions': '这是检索选择的独立函数调用。输出指定JSON，不执行其他任务。', 'dynamicTools': [], 'config': {'model_reasoning_effort': effort}})
        if thread.get('model') != self.model or thread.get('modelProvider') != 'openai':
            raise RuntimeError('Requested model/OpenAI was not selected: ' + self.model)
        tid = thread['thread']['id']
        events = queue.Queue()
        self.events[tid] = events
        opened = time.monotonic()
        texts = []
        usage = {}
        counts = {}
        turn_started = None
        first_text = None
        waited = 0
        try:
            if self.window_limit:
                with self.rate_lock:
                    now = time.monotonic()
                    while self.turn_starts and now - self.turn_starts[0] >= self.window_seconds:
                        self.turn_starts.popleft()
                    if len(self.turn_starts) >= self.window_limit:
                        waited = self.window_seconds - (now - self.turn_starts[0])
                        time.sleep(waited)
                        now = time.monotonic()
                        while self.turn_starts and now - self.turn_starts[0] >= self.window_seconds:
                            self.turn_starts.popleft()
                    self.turn_starts.append(now)
            turn = self.rpc('turn/start', {'threadId': tid, 'model': self.model, 'effort': effort, 'input': [{'type': 'text', 'text': json.dumps(payload, ensure_ascii=False, separators=(',', ':')), 'text_elements': []}], 'outputSchema': schema or SCHEMA})
            deadline = time.monotonic() + 90
            while True:
                try:
                    event = events.get(timeout=max(0.01, deadline - time.monotonic()))
                except queue.Empty:
                    raise TimeoutError('Model turn timed out: ' + self.model) from None
                method = event.get('method')
                params = event.get('params', {})
                now = time.monotonic()
                if method == 'turn/started':
                    turn_started = now
                if method == 'item/agentMessage/delta' and first_text is None:
                    first_text = now
                if method == 'thread/tokenUsage/updated':
                    usage = params.get('tokenUsage', {}).get('last', {})
                if method in ['item/started', 'item/completed']:
                    item = params.get('item', {})
                    kind = item.get('type', 'unknown')
                    if method == 'item/started':
                        counts[kind] = counts.get(kind, 0) + 1
                    if kind not in {'agentMessage', 'userMessage', 'reasoning', 'error'}:
                        self.rpc('turn/interrupt', {'threadId': tid, 'turnId': turn['turn']['id']})
                        raise ValueError('Unexpected tool/item in inference-only benchmark: ' + kind)
                    if method == 'item/completed' and kind == 'agentMessage':
                        texts.append(item['text'])
                if method == 'error' and (not params.get('willRetry', False)):
                    raise RuntimeError('Codex inference error: ' + json.dumps(params.get('error', {}), ensure_ascii=False))
                if method == 'turn/completed':
                    done = params['turn']
                    if done['status'] != 'completed':
                        raise RuntimeError(self.model + ' turn ' + done['status'] + ': ' + json.dumps(done.get('error')))
                    break
            ended = time.monotonic()
            result = json.loads(texts[-1])
            return (result, {'seconds': round(ended - started, 6), 'thread_setup_seconds': round(opened - started, 6), 'rate_wait_seconds': round(waited, 6), 'active_seconds': round(ended - started - waited, 6), 'turn_seconds': round(ended - opened, 6), 'first_text_seconds': round(first_text - opened, 6) if first_text else None, 'selected_model': thread['model'], 'selected_provider': thread['modelProvider'], 'ephemeral': True, 'tool_calls': 0, 'item_counts': counts, 'usage': {'prompt_tokens': usage.get('inputTokens', 0), 'completion_tokens': usage.get('outputTokens', 0), 'total_tokens': usage.get('totalTokens', 0), 'cached_prompt_tokens': usage.get('cachedInputTokens', 0), 'reasoning_tokens': usage.get('reasoningOutputTokens', 0)}})
        finally:
            self.events.pop(tid, None)
            self.rpc('thread/unsubscribe', {'threadId': tid})

    def close(self):
        self.process.terminate()
        try:
            self.process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            self.process.kill()
            self.process.wait()
        self.temp.cleanup()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
