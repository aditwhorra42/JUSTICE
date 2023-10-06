# JUSTICE
JUSTICE is an open-source Integrated Assessment Modeling Framework for Normative Uncertainty Analysis

# JUSTICE Integrated Assessment Framework

JUSTICE (JUST Integrated Climate Economy) is an Integrated Assessment Modelling Framework designed to explore the influence on distributive justice outcomes due to underlying modelling assumptions across model components and functions: the economy and climate components, and the damage and social welfare functions. JUSTICE is a simple IAM inspired by the long-established RICE and RICE50+, and is designed to be a surrogate for more complex IAMs for eliciting normative insights.

<img title="JUSTICE Framework" alt="Flowchart of JUSTICE" src="/docs/diagrams/JUSTICE Flowchart.jpeg">


```plaintext
📂 JUSTICE
┣ 📂 .github
┃ ┗ 📂 workflows
┃    ┗ 📜 main.yml         # GitHub Actions for CI/CD workflows
┣ 📂 src
┃ ┣ 📂 economy
┃ ┣ 📂 emissions
┃ ┣ 📂 climate
┃ ┣ 📂 damage
┃ └ 📂 welfare
┣ 📂 data
┃ ┣ 📂 input
┃ └ 📂 output
┣ 📂 docs                  # Documentation using sphinx/read-the-docs
┃ ┗ 📂 source
┃    ┣ 📜 conf.py          # Sphinx config
┃    ┣ 📜 index.rst        # Documentation home page
┃    ┣ 📜 economy.rst      # Documentation for economy module
┃    ┣ 📜 emissions.rst    # Documentation for emissions module, and so on..
┃    ┣ 📜 climate.r
┃    ┣ 📜 damage.rst    # Documentation for damage module
┃    └ 📜 welfare.rst   # Documentation for welfare module
┣ 📂 tests                     # Unit tests for your project
┃   ┣ 📜 test_economy.py
┃   ┣ 📜 test_emissions.py 
┃   ┣ 📜 test_climate.py
┃   ┣ 📜 test_damage.py
┃   └ 📜 test_welfare.py
┣ 📜 .gitignore                # File listing what to ignore in Git
┣ 📜 README.md                 # Readme for your repo, can also include project wide documentation
┗ 📜 LICENSE.md                # File that contains license for the project
```