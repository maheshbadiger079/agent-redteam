from setuptools import setup, find_packages

setup(
    name="agent-redteam-harness",
    version="0.1.0",
    description="Attack AI agents on purpose and score how well they hold up (OWASP LLM Top 10).",
    packages=find_packages(),
    package_data={
        "attacks": ["*.yaml"],
        "": ["attacks/*.yaml"],
    },
    include_package_data=True,
    install_requires=[
        "pyyaml>=6.0",
        "requests>=2.32",
        "fastapi>=0.110.0",
        "slowapi>=0.1.9",
        "pydantic>=2.0",
    ],
    entry_points={
        "console_scripts": [
            "redteam-harness=harness.runner:main",
            "redteam-report=harness.report:main",
        ],
    },
    python_requires=">=3.9",
)

