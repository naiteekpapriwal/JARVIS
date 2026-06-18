import yaml
from mem0 import Memory
with open("config.yaml", "r") as f:
    c = yaml.safe_load(f)

mem0_config = {
    "llm": {"provider": "ollama", "config": {"model": c["ollama"]["model"], "ollama_base_url": c["ollama"]["base_url"]}},
    "embedder": {"provider": "ollama", "config": {"model": c["ollama"]["embedding_model"], "ollama_base_url": c["ollama"]["base_url"]}},
    "vector_store": {"provider": "chroma", "config": {"collection_name": c["memory"]["collection"], "path": c["memory"]["db_path"]}}
}
m = Memory.from_config(mem0_config)

print("Starting add...")
try:
    m.add("User: I live in Paris\nAssistant: That is a beautiful city!", user_id="naiteek")
    print("Add successful")
except Exception as e:
    print("Add failed:", str(e))
