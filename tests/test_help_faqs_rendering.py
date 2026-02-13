from src.main import create_app


def test_help_faqs_render_list_answer(tmp_path):
    faqs_path = tmp_path / "help_faqs.yaml"
    faqs_path.write_text(
        "- question: \"How to change settings?\"\n"
        "  answer:\n"
        "    - \"Step one\"\n"
        "    - \"Step two\"\n",
        encoding="utf-8",
    )

    app = create_app()
    app.config.update(
        TESTING=True,
        HELP_FAQS_PATH=str(faqs_path),
    )
    client = app.test_client()

    res = client.get("/")
    assert res.status_code == 200
    assert b"<ul>" in res.data
    assert b"Step one" in res.data
    assert b"Step two" in res.data
