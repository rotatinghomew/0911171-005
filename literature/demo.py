from .notebook import ResearchNotebook


def main() -> None:
    rows = [{"chapter": "c1", "character": "third prince", "revision": 1, "mentions": 3}]
    notebook = ResearchNotebook([{"chapter": "c1"}, {"chapter": "c2"}])
    print(notebook.describe("draft", rows, {"third prince": "third"}, {"c1", "c2"}, "census"))
    print(notebook.evidence("draft", "third"))


if __name__ == "__main__":
    main()
