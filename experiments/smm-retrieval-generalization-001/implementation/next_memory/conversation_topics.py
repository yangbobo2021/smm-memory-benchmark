"""Source-bound topic navigation, without a synthesized fact store or vectors.

This experimental index stores overviews and original hashes, never originals.
The owner of a source remains responsible for storing and explicitly opening it.
"""
import datetime
import hashlib
import json
import re
import sqlite3


def canonical_time(value):
    d = datetime.datetime.fromisoformat(value.replace('Z', '+00:00'))
    if d.tzinfo is None:
        raise ValueError('An explicit source timezone is required')
    return d.astimezone(datetime.timezone.utc).isoformat()


def validate_topics(topics, original):
    if not isinstance(topics, list) or not 1 <= len(topics) <= 8:
        raise ValueError('Expected 1..8 topics per original')
    for topic in topics:
        if not isinstance(topic, dict) or set(topic) != {'label', 'cues'}:
            raise ValueError('A topic contains only label and cues')
        label, cues = topic['label'], topic['cues']
        if not isinstance(label, str) or not 1 <= len(label.strip()) <= 120:
            raise ValueError('Invalid navigation label')
        if not isinstance(cues, list) or len(cues) > 4:
            raise ValueError('At most four local source cues per topic')
        if any(not isinstance(c, str) or not 1 <= len(c) <= 80 or c not in original for c in cues):
            raise ValueError('Every cue must be an exact original substring, <=80 characters')
    return topics


def lexical_expression(question):
    # No synonyms, query expansion, answer lookup or vector matching.
    tokens = list(dict.fromkeys(re.findall(r'[^\W_]+', question.casefold(), re.UNICODE)))
    return ' OR '.join('"' + token + '"' for token in tokens[:128])


class ConversationTopics:
    def __init__(self, path):
        self.db = sqlite3.connect(path)
        self.db.row_factory = sqlite3.Row
        self.db.executescript('''
          create table if not exists sources(
            id text primary key, source_sha256 text not null, authored_at text not null,
            topics_json text not null);
          create virtual table if not exists topic_fts using fts5(
            source_id UNINDEXED, content, tokenize='porter unicode61');
        ''')

    def add(self, source_id, original, authored_at, topics):
        """Publish source-derived navigation atomically; never update source facts."""
        validate_topics(topics, original)
        authored_at = canonical_time(authored_at)
        digest = hashlib.sha256(original.encode()).hexdigest()
        payload = json.dumps(topics, ensure_ascii=False, sort_keys=True)
        existing = self.db.execute('select * from sources where id=?', (source_id,)).fetchone()
        if existing:
            if (existing['source_sha256'], existing['authored_at'], existing['topics_json']) != (digest, authored_at, payload):
                raise ValueError('Source binding or topic version differs; publish a separate index revision')
            return
        content = '\n'.join(t['label'] + '\n' + ' '.join(t['cues']) for t in topics)
        with self.db:
            self.db.execute('insert into sources values(?,?,?,?)', (source_id, digest, authored_at, payload))
            self.db.execute('insert into topic_fts values(?,?)', (source_id, content))

    @staticmethod
    def overview(row):
        return {'source_id': row['id'], 'source_sha256': row['source_sha256'],
                'authored_at': row['authored_at'], 'topics': json.loads(row['topics_json']),
                'kind': 'navigation-only; open original before making factual claims'}

    def menu(self, *, known_at):
        return [self.overview(r) for r in self.db.execute(
            'select * from sources where authored_at<=? order by id', (canonical_time(known_at),))]

    def search(self, question, *, known_at, limit=5):
        if type(limit) is not int or not 1 <= limit <= 64:
            raise ValueError('Candidate limit must be 1..64')
        expression = lexical_expression(question)
        if not expression:
            return []
        rows = self.db.execute('''select s.*,bm25(topic_fts) as score
          from topic_fts join sources s on s.id=topic_fts.source_id
          where topic_fts match ? and s.authored_at<=?
          order by bm25(topic_fts),s.id limit ?''', (expression, canonical_time(known_at), limit))
        return [self.overview(r) | {'score': r['score']} for r in rows]

    def close(self):
        self.db.close()


def score_ranking(ranked, required):
    """Keep first-hit, all-record coverage and record recall separate."""
    if len(ranked) != len(set(ranked)):
        raise ValueError('Duplicate source in a ranking')
    required = set(required)
    if not required:
        raise ValueError('No positive retrieval label; do not count as a hit or miss')
    first = next((i for i, rid in enumerate(ranked, 1) if rid in required), None)
    return {'first_hit_rank': first, 'required_count': len(required), 'by_k': {
        str(k): {'hit': bool(set(ranked[:k]) & required),
                 'all_required': required <= set(ranked[:k]),
                 'records_hit': len(set(ranked[:k]) & required),
                 'records_total': len(required)} for k in range(1, 6)}}
