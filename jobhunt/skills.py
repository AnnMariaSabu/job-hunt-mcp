"""Find skills in job text and compare them with my resume skills.

Plain code, no AI: a list of known skills plus other ways people write them
(aliases), searched with regular expressions. Fast, free, and easy to check.
Only TECHNICAL skills are listed. Soft skills ("communication") are left out on
purpose, because almost every job asks for them.
"""

import re
from functools import lru_cache

# canonical name -> other ways a job post may write it
SKILL_CATALOG: dict[str, list[str]] = {
    # Programming
    "python": ["python"],
    "sql": ["sql", "mysql", "postgresql", "postgres", "sqlite", "t-sql", "pl/sql"],
    "r": ["r programming", "r language", "rstudio"],
    "c": ["c programming", "c language", "c/c++"],  # never the bare letter "c"
    "java": ["java"],
    "javascript": ["javascript", "typescript", "node.js", "nodejs"],
    "c++": ["c++"],
    "git": ["git", "github", "gitlab"],
    "linux": ["linux", "bash", "shell scripting"],
    # Data analysis
    "pandas": ["pandas"],
    "numpy": ["numpy"],
    "excel": ["excel", "ms excel", "microsoft excel", "spreadsheet"],
    "power bi": ["power bi", "powerbi"],
    "tableau": ["tableau"],
    "statistics": ["statistics", "statistical"],
    "data analysis": ["data analysis", "data analytics", "analyze data", "analyse data"],
    "data cleaning": ["data cleaning", "data cleansing", "data wrangling", "data preprocessing"],
    "data visualization": ["data visualization", "data visualisation", "dashboard"],
    # Machine learning / AI
    "machine learning": ["machine learning", "ml"],
    "deep learning": ["deep learning", "neural network"],
    "scikit-learn": ["scikit-learn", "sklearn"],
    "tensorflow": ["tensorflow", "keras"],
    "pytorch": ["pytorch", "torch"],
    "nlp": ["nlp", "natural language processing"],
    "computer vision": ["computer vision", "opencv", "image processing"],
    "llm": ["llm", "large language model", "generative ai", "genai", "gen ai", "gpt"],
    "rag": ["rag", "retrieval augmented generation"],
    "langchain": ["langchain"],
    "llamaindex": ["llamaindex", "llama index"],
    "prompt engineering": ["prompt engineering"],
    "vector databases": ["vector database", "vector db", "vector store", "faiss",
                         "pinecone", "chromadb", "weaviate", "qdrant"],
    "hugging face": ["hugging face", "huggingface", "transformers"],
    "embeddings": ["embedding", "vector embedding", "sentence embedding"],
    "ai agents": ["ai agent", "agentic", "llm agent", "autonomous agent", "multi agent"],
    "tool calling": ["tool calling", "function calling", "tool use"],
    "mcp": ["mcp", "model context protocol", "model context protocol (mcp)"],
    "llm evaluation": ["llm evaluation", "evals", "rag evaluation", "ai evaluation"],
    "mlops": ["mlops", "mlflow", "model deployment"],
    # Engineering / data engineering
    "fastapi": ["fastapi"],
    "flask": ["flask"],
    "rest api": ["rest api", "restful", "rest apis"],
    "docker": ["docker"],
    "kubernetes": ["kubernetes", "k8s"],
    "aws": ["aws", "amazon web services"],
    "azure": ["azure"],
    "gcp": ["gcp", "google cloud"],
    "etl": ["etl", "elt", "data pipeline"],
    "spark": ["spark", "pyspark"],
    "hadoop": ["hadoop"],
    "airflow": ["airflow"],
    "kafka": ["kafka"],
    "data warehousing": ["data warehouse", "data warehousing", "snowflake", "bigquery",
                         "redshift"],
    "dbt": ["dbt"],
    "nosql": ["nosql", "mongodb", "cassandra"],
    "streamlit": ["streamlit"],
}


def normalize(text: str) -> str:
    """Lowercase, treat - and _ like spaces, squash extra spaces.
    So 'Scikit-Learn' and 'scikit learn' look the same."""
    text = text.lower().replace("-", " ").replace("_", " ")
    return re.sub(r"\s+", " ", text).strip()


def canonical(skill: str) -> str:
    """The standard name of a skill: 'sklearn' -> 'scikit-learn'.
    Unknown skills just get normalized: 'Some Tool' -> 'some tool'."""
    norm = normalize(skill)
    for name, aliases in SKILL_CATALOG.items():
        if norm == normalize(name) or norm in (normalize(a) for a in aliases):
            return name
    return norm


@lru_cache(maxsize=None)
def _pattern(phrase: str) -> re.Pattern:
    """Regex for one phrase as a whole word, with an optional plural 's'.

    (?<!\\w) and (?!\\w) mean "no letter or digit right before / after", so
    'java' does not match inside 'javascript', and 'c++' still works.
    """
    words = [re.escape(w) for w in normalize(phrase).split(" ")]
    return re.compile(r"(?<!\w)" + r"\s+".join(words) + r"s?(?!\w)")


def mentions(text: str, phrase: str) -> bool:
    """True if `phrase` appears in `text` as whole words (any case, any dashes)."""
    return bool(_pattern(phrase).search(normalize(text)))


def extract_skills(text: str, extra_skills: list[str] = ()) -> list[str]:
    """All known skills mentioned in the text (canonical names, sorted).

    extra_skills: my own resume skills, so a skill that is not in the catalog
    still gets found if the job mentions it.
    """
    norm = normalize(text)
    found = set()
    # We search the ALIASES only (they include the name when that is safe).
    # The bare name "r" would wrongly match "Rs. 5 LPA" or "R&D".
    for name, aliases in SKILL_CATALOG.items():
        if any(_pattern(phrase).search(norm) for phrase in aliases):
            found.add(name)
    for skill in extra_skills:
        if canonical(skill) not in SKILL_CATALOG and _pattern(skill).search(norm):
            found.add(canonical(skill))
    return sorted(found)


def match_skills(job_text: str, my_skills: list[str]) -> dict:
    """Compare the job's skills with mine.

    Example: job wants {python, sql, docker}, I have {python, sql, excel}
      -> matched [python, sql], gaps [docker], match_percent 66.7
    """
    mine = {canonical(s) for s in my_skills}
    wanted = set(extract_skills(job_text, extra_skills=list(my_skills)))
    matched = sorted(wanted & mine)
    gaps = sorted(wanted - mine)
    percent = round(100 * len(matched) / len(wanted), 1) if wanted else None
    return {"match_percent": percent, "job_skills": sorted(wanted),
            "matched_skills": matched, "skill_gaps": gaps}
