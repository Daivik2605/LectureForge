def test_backend_imports() -> None:
    import app.main  # noqa: F401
    import app.services.ppt_pipeline  # noqa: F401
    import app.services.pdf_pipeline  # noqa: F401
    import app.services.policy_pipeline  # noqa: F401
