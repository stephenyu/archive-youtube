This project uses 'uv' for dependency management. Please refer to `README.md` for the source of truth regarding application setup, installation, and usage.

### Testing Policy for Gemini Interactions

When making any changes to the codebase, including bug fixes, new features, or refactoring, the following testing policy must be adhered to:

-   **Run Existing Tests:** Always run the project's existing test suite to ensure no regressions are introduced.
-   **Update Tests:** If code changes alter existing functionality or expected behavior, update the relevant tests to reflect these changes.
-   **Add New Tests:** For new features or significant modifications, new tests (unit, integration, or end-to-end as appropriate) must be added to cover the new or changed logic.

This ensures the continuous quality and stability of the application. Refer to `README.md` for instructions on how to run tests.