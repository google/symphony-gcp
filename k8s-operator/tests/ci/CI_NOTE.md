CI Test Guidance (kind-tests)

This note documents the filename and run convention for tests in the `kind-tests` folder so new files stay aligned and easy to find.

- Filename pattern: use a descriptive prefix `test_`, then a short title and a test type.
	- Format: `test_<title>_<test-type>.sh` - e.g. `test_gcpsr_create_assert.sh` or `test_mrr_return_integration.sh`.
	- Suggested `test-type` values: `assert`, `integration`, `smoke`.

	- Examples:
		- GCP Symphony Resource: `test_gcpsr_create_assert.sh`.
		- Machine Return Request: `test_mrr_return_integration.sh`.

	Note: `gcpsr` and `mrr` are category names and may both appear in filenames; keep names clear and consistent.

- Test script header: every test script must include a short header immediately after the shebang `(#!)` describing the test purpose. Example header lines:
  ```bash
  # Purpose: Short description of what this test asserts or sets up.
  # Run from k8s-operator/tests/ci/kind-tests with an isolated Kubernetes context.
  ```

- Running locally: run tests from the repo in the same shell session so env vars and virtualenvs persist. Ensure you are using an isolated Kubernetes `kubectl` context for CI tests. Example using `kind`:
	```bash
	# create an isolated kind cluster (one-off)
	kind create cluster --name ci
	kubectl config use-context kind-ci

	# run the test
	cd k8s-operator/tests/ci/kind-tests
	./test_gcpsr_create_assert.sh
	```

	Alternatively point `KUBECONFIG` at an isolated kubeconfig:
	```bash
	export KUBECONFIG=/path/to/isolated/kubeconfig
	kubectl config current-context
	```

CI runners typically sort filenames lexicographically. Without numeric prefixes the ordering is alphabetical — choose descriptive names to avoid accidental reordering.

