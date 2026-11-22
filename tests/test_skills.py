import config
from jobhunt import data_files, db, matching, skills, tracker


def test_canonical_names():
    assert skills.canonical("Scikit-Learn") == "scikit-learn"
    assert skills.canonical("sklearn") == "scikit-learn"
    assert skills.canonical("PowerBI") == "power bi"
    assert skills.canonical("Some New Tool") == "some new tool"


def test_extract_finds_aliases_and_plurals():
    text = "Must know Python, MySQL, PowerBI dashboards and LLMs (GenAI)."
    assert skills.extract_skills(text) == [
        "data visualization", "llm", "power bi", "python", "sql"]


def test_extract_respects_word_boundaries():
    assert "java" not in skills.extract_skills("We use JavaScript")
    assert "c++" in skills.extract_skills("Strong C++ skills")
    assert "machine learning" not in skills.extract_skills("Write HTML pages")
    assert "r" not in skills.extract_skills("Salary Rs. 5 LPA, R&D team")


def test_ai_engineer_words_are_recognised():
    text = "Agentic AI with function calling, evals, MCP, embeddings. C/C++ helpful."
    assert skills.extract_skills(text) == [
        "ai agents", "c", "c++", "embeddings", "llm evaluation", "mcp", "tool calling"]
    assert skills.canonical("Model Context Protocol (MCP)") == "mcp"
    assert "c" not in skills.extract_skills("CS degree, grade C")  # never the bare letter


def test_match_percent_and_gaps():
    result = skills.match_skills("Python, SQL and Docker needed", ["Python", "SQL", "Excel"])
    assert result["matched_skills"] == ["python", "sql"]
    assert result["skill_gaps"] == ["docker"]
    assert result["match_percent"] == 66.7


def test_match_resume_uses_example_data_and_saves_percent():
    job_id = tracker.add_job(
        "https://example.com/ai-job", company="Acme", role="AI Engineer",
        description="Build RAG apps with Python, LangChain and a vector database. Docker is a plus.",
    )["job_id"]
    result = matching.match_resume(job_id)
    assert result["matched_skills"] == ["langchain", "python", "rag"]
    assert result["skill_gaps"] == ["docker", "vector databases"]
    assert result["match_percent"] == 60.0
    assert result["supporting_bullets"][0]["id"] == "rag-bot"  # proves 3 skills
    assert "EXAMPLE" in result["warning"]
    assert db.get_job(job_id)["match_percent"] == 60.0


def test_match_resume_without_description_explains_what_to_do():
    job_id = tracker.add_job("https://example.com/x", role="Accountant")["job_id"]
    result = matching.match_resume(job_id)
    assert result["match_percent"] is None
    assert "description" in result["message"]


def test_example_data_passes_safety_check():
    resume_skills = data_files.load_resume()["skills"]
    bullets = data_files.load_yaml(config.MASTER_BULLETS_PATH)["bullets"]
    assert data_files.check_bullets(bullets, resume_skills) == []


def test_safety_check_catches_invented_skill_and_duplicate_id():
    bullets = [
        {"id": "a", "text": "Did a thing", "skills": ["Python"]},
        {"id": "a", "text": "Did Docker things", "skills": ["Docker"]},
    ]
    problems = data_files.check_bullets(bullets, ["Python"])
    assert "a: id used twice" in problems
    assert "a: skill 'Docker' is not in master_resume.yaml" in problems
