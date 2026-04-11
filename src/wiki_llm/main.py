from wiki_llm.config import settings


def main() -> None:
    print(f"Workspace: {settings.workspace}")
    print(f"Wiki dir:  {settings.wiki_dir}")
    print(f"LLM model: {settings.llm_model}")
    print(f"Transport: {settings.mcp_transport}")
