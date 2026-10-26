# Attribution and artifact scope

The benchmark contains a fixed derivative subset of **LongMemEval-cleaned** by Di Wu and collaborators:

- Dataset: https://huggingface.co/datasets/xiaowu0162/longmemeval-cleaned
- Frozen dataset revision: `98d7416c24c778c2fee6e6f3006e7a073259d48f`
- Upstream repository: https://github.com/xiaowu0162/LongMemEval
- Frozen code revision: `9e0b455f4ef0e2ab8f2e582289761153549043fc`
- Upstream MIT notice: [LongMemEval-MIT.txt](experiments/smm-baseline-001/licenses/LongMemEval-MIT.txt)
- File-level provenance: [dataset.json](experiments/smm-baseline-001/provenance/dataset.json)

The frozen dataset card declares `license: mit`; its SHA256 is `fe31783d4e5d132681a25e4192e85def8edd214094939879f5283818c0a4a3e0`. The card and upstream license were checked before publication. Copyright in upstream material remains with its original holders. Historical conversations are public benchmark material, not the repository owner's private chat history.

The root MIT license applies to original repository code and documentation. It does not imply ownership of third-party material or independently relicense model providers' software. Archived model responses are published as experimental observations with their provider/configuration provenance; any applicable service terms remain relevant to reuse. These are not provider-endorsed scores or verified real-world facts stated inside the historical conversations.

The publication directory adds navigation and integrity tooling around the sealed experiment. It does not alter source conversations, frozen prompts, raw outputs, reference answers, or archived grades. Historical paths, runtime identifiers, and model-list metadata remain as audit data; no authentication material is included.

## LoCoMo retrieval validation

`experiments/smm-retrieval-generalization-001` also contains original and derived **LoCoMo** text from Snap Research, by Adyasha Maharana, Dong-Ho Lee, Sergey Tulyakov, Mohit Bansal, Francesco Barbieri and Yuwei Fang (*Evaluating Very Long-Term Conversational Memory of LLM Agents*, ACL 2024). Upstream: https://github.com/snap-research/locomo, commit `3eb6f2c585f5e1699204e3c3bdf7adc5c28cb376`.

LoCoMo material retains its **Creative Commons Attribution-NonCommercial 4.0 International** license, reproduced at [LoCoMo-CC-BY-NC-4.0.txt](experiments/smm-retrieval-generalization-001/licenses/LoCoMo-CC-BY-NC-4.0.txt), and is **not relicensed under the root MIT license**. The retrieval experiment selects questions, serializes original dated sessions with speaker labels, and derives text embeddings and rankings; its method and file provenance identify those transformations. It does not rewrite the original utterance text or distribute the source images. The study is published for noncommercial research reference. The new LongMemEval slice retains its existing MIT attribution separately.
