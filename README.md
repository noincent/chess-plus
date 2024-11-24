# CHESS+: Enhanced Contextual SQL Synthesis with Chat Capabilities

This repository contains an enhanced version of CHESS (Contextual Harnessing for Efficient SQL Synthesis), extending it with interactive chat capabilities and additional components.

## Original CHESS Framework
This project builds upon the original CHESS framework, which addresses text-to-SQL translation through four specialized agents:

1. **Information Retriever (IR)**: Extracts relevant data
2. **Schema Selector (SS)**: Prunes large schemas
3. **Candidate Generator (CG)**: Generates high-quality candidates
4. **Unit Tester (UT)**: Validates queries through LLM-based testing

## New Features

### Interactive Chat Capabilities
The enhanced version introduces interactive chat functionality through new specialized components:

1. **Chat Context Analyzer**: Understands user intent and conversation flow
2. **Response Generator**: Produces natural language responses
3. **SQL Executor**: Manages query execution and result formatting
4. **Enhanced Information Retriever**: Improved keyword extraction and context management

### Key Enhancements
- **Interactive Sessions**: Maintain context across multiple queries
- **Natural Conversations**: More intuitive interaction with the SQL generation system
- **Result Formatting**: Clean presentation of query results
- **Context-Aware Responses**: Improved understanding of follow-up questions

## Setting up the Environment

1. **Clone the repository**:
    ```bash
    git clone https://github.com/yourusername/CHESS.git
    cd CHESS
    ```

2. **Create a `.env` file** in the root directory with your configuration:
    ```bash
    DATA_MODE="dev"
    DATA_PATH="./data/dev/dev.json"
    DB_ROOT_DIRECTORY="./data/dev/dev_databases"
    DATA_TABLES_PATH="./data/dev/dev_tables.json"
    INDEX_SERVER_HOST='localhost'
    INDEX_SERVER_PORT=12345

    OPENAI_API_KEY=
    GCP_PROJECT=''
    GCP_REGION='us-central1'
    GCP_CREDENTIALS=''
    GOOGLE_CLOUD_PROJECT=''
    ```

3. **Install required packages**:
    ```bash
    pip install -r requirements.txt
    ```

## Preprocessing

To retrieve database catalogs and find the most similar database values to a question, preprocess the databases:

1. **Run the preprocessing script**:
    ```bash
    sh run/run_preprocess.sh
    ```

    This will create the minhash, LSH, and vector databases for each of the databases in the specified directory.

## Running the Code

After preprocessing the databases, generate SQL queries for the BIRD dataset by choosing a configuration:

1. **Run the main script**:
    ```bash
    sh run/run_main_ir_cg_ut.sh
    ```

    or

    ```bash
    sh run/run_main_ir_ss_ch.sh
    ```

## Sub-sampled Development Set (SDS)

The sub-sampled development set (SDS) is a subset of the BIRD dataset with 10% of samples from each database. It is used for ablation studies and is available in `sub_sampled_bird_dev_set.json`.

## Supporting Other LLMs

To use your own LLM, modify the `get_llm_chain(engine, temperature, base_uri=None)` function and add your LLM in `run/langchain_utils.py`.

## Using Chat Features

To interact with the system using chat:

1. **Start a chat session**:
    ```bash
    python interface.py --mode chat
    ```

2. **Ask questions naturally**, for example:
    - "Show me all employees in the Sales department"
    - "How many of them were hired last year?"
    - "What's the average salary?"

The system will maintain context across questions and provide formatted responses.

## Attribution

This project is based on the original CHESS framework. If you use this enhanced version in your research, please cite both this repository and the original CHESS paper:

```bibtex
@article{talaei2024chess,
  title={CHESS: Contextual Harnessing for Efficient SQL Synthesis},
  author={Talaei, Shayan and Pourreza, Mohammadreza and Chang, Yu-Chen and Mirhoseini, Azalia and Saberi, Amin},
  journal={arXiv preprint arXiv:2405.16755},
  year={2024}
}
```