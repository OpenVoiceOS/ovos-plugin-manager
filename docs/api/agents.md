# Agent & Solver Plugins

OVOS provides two generations of NLP backend plugins:

- **Agent engines** (`opm.agents.*`) — current, actively developed
- **Solver plugins** (`opm.solver.*`) — **deprecated**, will be removed in the next major release

Both live in `ovos_plugin_manager.templates.agents` and
`ovos_plugin_manager.templates.solvers` respectively.

---

## Agent Engines (current)

All agent engines ultimately derive from `AbstractAgentEngine` (in
`ovos_plugin_manager.thirdparty.solvers` / `AbstractSolver`).

### Common `AbstractSolver` constructor

```python
AbstractSolver(
    config: Optional[dict] = None,
    translator: Optional[LanguageTranslator] = None,
    detector: Optional[LanguageDetector] = None,
    priority: int = 50,
    enable_tx: bool = False,
    enable_cache: bool = False,
    internal_lang: Optional[str] = None,
)
```

| Attribute | Description |
|---|---|
| `default_lang` | Internal language (BCP-47). Queries not in `supported_langs` are auto-translated. |
| `supported_langs` | Languages the plugin natively supports (from config). |
| `enable_tx` | If `True`, inputs are translated to `default_lang` and outputs translated back. |
| `enable_cache` | Cache results on disk via `JsonStorageXDG`. |
| `priority` | Solver priority (lower = higher priority). Default 50. |

### Auto-translation decorators

`@auto_translate(translate_keys=[...])` and `@auto_detect_lang(text_keys=[...])` can be
applied to solver methods to transparently handle translation.

---

### `ChatEngine`

**Entry point:** `opm.agents.chat`

Streaming/non-streaming conversational LLM backend.

#### Abstract method

```python
def continue_chat(self, messages: List[AgentMessage],
                  session_id: str = "default",
                  lang: Optional[str] = None,
                  units: Optional[str] = None) -> AgentMessage
```

Generate a response given a list of `AgentMessage` objects.

---

### `AgenticLoopEngine`

**Entry point:** `opm.agents.loop`

A `ChatEngine` subclass for plugins that implement an internal agent loop (ReAct, tool-call/observe, background workers, etc.). Callers treat it identically to `ChatEngine` — the loop is an implementation detail.

Adds a standard toolbox registration interface:

```python
def load_toolboxes(self, toolboxes: List[ToolBox]) -> None
```

Called by the persona loader when the persona config declares a `toolboxes` list. Plugins may also discover and load toolboxes internally.

Persona config example:

```json
{
  "name": "MyAgent",
  "solvers": ["ovos-react-agent"],
  "toolboxes": ["web_search_tools", "file_tools"]
}
```

See [Agent Tools](agent-tools.md) for the `ToolBox` plugin API.

---

### `RetrievalEngine`

**Entry point:** `opm.agents.retrieval`

Base for retrieval-augmented generation backends.

---

### `DocumentIndexerEngine`

**Entry point:** `opm.agents.retrieval.documents`

Index and search a corpus of documents.

---

### `QAIndexerEngine`

**Entry point:** `opm.agents.retrieval.qa`

QA-specific retrieval over a question→answer corpus.

---

### `ReRankerEngine`

**Entry point:** `opm.agents.reranker`

Rank a list of candidates by relevance to a query.

---

### `SummarizerEngine`

**Entry point:** `opm.agents.summarizer`

Summarize a document.

---

### `ExtractiveQAEngine`

**Entry point:** `opm.agents.extractive_qa`

Extract the best passage from a document that answers a question.

---

### `NaturalLanguageInferenceEngine`

**Entry point:** `opm.agents.nli`

Determine whether a premise entails a hypothesis.

---

### `AgentContextManager`

**Entry point:** `opm.agents.memory`

Manage conversational context / session memory for agent plugins.

```python
from ovos_plugin_manager.templates.agents import AgentContextManager, AgentMessage
```

#### Abstract methods

```python
def get_history(self, session_id: str) -> List[AgentMessage]
def update_history(self, new_messages: List[AgentMessage], session_id: str)
```

#### Property

```python
@property
def system_prompt(self) -> str
```

Returns the system prompt string from config (`config['system_prompt']`).

---

### `AgentMessage` dataclass

```python
from ovos_plugin_manager.templates.agents import AgentMessage, MessageRole
```

| Field | Type | Description |
|---|---|---|
| `role` | `MessageRole` | `SYSTEM`, `DEVELOPER`, `USER`, or `ASSISTANT`. |
| `content` | `str` | Message text. |

---

## Deprecated Solver Plugins

> These classes are in `ovos_plugin_manager.templates.solvers` and will be removed in the
> next major release. Migrate to the corresponding agent engines.

| Deprecated class | Replacement |
|---|---|
| `QuestionSolver` | `ChatEngine` / `RetrievalEngine` |
| `ChatMessageSolver` | `ChatEngine` |
| `CorpusSolver` | `DocumentIndexerEngine` / `QAIndexerEngine` |
| `TldrSolver` | `SummarizerEngine` |
| `EvidenceSolver` | `ExtractiveQAEngine` |
| `MultipleChoiceSolver` | `ReRankerEngine` |
| `EntailmentSolver` | `NaturalLanguageInferenceEngine` |

### `QuestionSolver` (deprecated)

**Entry point:** `opm.solver.question`

#### Abstract method

```python
def get_spoken_answer(self, query: str, lang: Optional[str] = None, units: Optional[str] = None) -> Optional[str]
```

#### Public methods (with auto-translation)

- `spoken_answer(query, lang, units)` — return spoken answer string
- `search(query, lang, units)` — return data dict (cached)
- `visual_answer(query, lang, units)` — return image path/URL
- `long_answer(query, lang, units)` — return `[{"title", "summary", "img"}, ...]`
- `stream_utterances(query, lang, units)` — yield answer sentences

### `TldrSolver` (deprecated)

**Entry point:** `opm.solver.summarization`

#### Abstract method

```python
def get_tldr(self, document: str, lang: Optional[str] = None) -> str
```

#### Public method

- `tldr(document, lang)` — with auto-translation

### `EvidenceSolver` (deprecated)

**Entry point:** `opm.solver.reading_comprehension`

#### Abstract method

```python
def get_best_passage(self, evidence: str, question: str, lang: Optional[str] = None) -> str
```

#### Public method

- `extract_answer(evidence, question, lang)` — with auto-translation

### `MultipleChoiceSolver` (deprecated)

**Entry point:** `opm.solver.multiple_choice`

#### Abstract method

```python
def rerank(self, query: str, options: List[str], lang: Optional[str] = None, return_index: bool = False) -> List[Tuple[float, Union[str, int]]]
```

#### Public method

- `select_answer(query, options, lang, return_index)` — returns best option (or its index)

### `EntailmentSolver` (deprecated)

**Entry point:** `opm.solver.entailment`

#### Abstract method

```python
def check_entailment(self, premise: str, hypothesis: str, lang: Optional[str] = None) -> bool
```

#### Public method

- `entails(premise, hypothesis, lang)` — with auto-translation
