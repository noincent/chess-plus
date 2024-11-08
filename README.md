# CHESS-Plus: Enhanced Contextual SQL Synthesis with Chat & Visualization

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Framework: LangChain](https://img.shields.io/badge/framework-langchain-green.svg)](https://python.langchain.com/)

CHESS-Plus extends the CHESS (Contextual Harnessing for Efficient SQL Synthesis) project with interactive chat capabilities, dynamic visualizations, and enhanced query processing. It transforms natural language into SQL queries while providing rich context, visual insights, and conversational interactions.

## 🌟 Key Features

- **All Original CHESS Features**
  - Efficient SQL query synthesis from natural language
  - Contextual schema understanding
  - Intelligent database catalog utilization
  - Support for complex, multi-table queries
  - Compatible with multiple LLM providers

- **New Enhanced Capabilities**
  - 💬 Interactive Chat Interface
    - Persistent chat sessions
    - Context-aware conversations
    - Query refinement through dialogue
    - Historical query reference

  - 📊 Dynamic Visualizations
    - Automatic visualization suggestions
    - Interactive React-based charts
    - Multiple visualization types
    - Custom visualization options

  - 🎯 Intent-Based Processing
    - Dynamic pipeline configuration
    - Query intent analysis
    - Optimized processing paths
    - Context-aware responses

## 🚀 Quick Start

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/chess-plus.git
   cd chess-plus
   ```

2. **Create and activate virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**
   ```bash
   cp env.example .env
   # Edit .env with your configuration
   ```

5. **Preprocess the databases**
   ```bash
   sh run/run_preprocess.sh
   ```

6. **Start the interactive interface**
   ```bash
   python src/interface.py
   ```

## 💻 Usage Examples

### Basic Query with Chat
```python
from chess_plus import SQLInterface

interface = SQLInterface()
session = interface.create_session(db_id="financial")

# Ask a question
response = session.query(
    "What were the total sales in 2023 by quarter?",
    include_viz=True
)

# Follow-up question using context
response = session.query(
    "How does that compare to 2022?",
    reference_previous=True
)
```

### Custom Visualization
```python
from chess_plus.visualization import VisualizationEngine

viz_engine = VisualizationEngine()
custom_viz = viz_engine.create(
    data=response.results,
    viz_type="bar_chart",
    options={
        "title": "Quarterly Sales Comparison",
        "x_label": "Quarter",
        "y_label": "Total Sales"
    }
)
```

## 🏗️ Architecture

```
chess-plus/
├── src/
│   ├── chat/          # Chat system components
│   ├── visualization/ # Visualization engine
│   ├── pipeline/      # Enhanced CHESS pipeline
│   └── interface.py   # Main interface
├── templates/         # Prompt templates
└── chat_sessions/    # Session storage
```

## 📊 Supported Visualizations

- Bar Charts
- Line Charts
- Scatter Plots
- Histograms
- Pie Charts
- Heat Maps
- Box Plots
- Area Charts

## 🛠️ Configuration

CHESS-Plus can be configured through both environment variables and runtime settings. Key configuration areas include:

- LLM Provider Selection
- Chat Context Window Size
- Visualization Defaults
- Pipeline Optimization Settings
- Database Connection Parameters

See `config.example.yaml` for detailed configuration options.

## 📝 Citation

If you use CHESS-Plus in your research, please cite:

```bibtex
@article{talaei2024chess,
  title={CHESS: Contextual Harnessing for Efficient SQL Synthesis},
  author={Talaei, Shayan and Pourreza, Mohammadreza and Chang, Yu-Chen and Mirhoseini, Azalia and Saberi, Amin},
  journal={arXiv preprint arXiv:2405.16755},
  year={2024}
}
```

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guidelines](CONTRIBUTING.md) for details on how to submit pull requests, report issues, and contribute to the project.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- The original CHESS project team
- All contributors and maintainers
- The open-source NLP and database communities

## 📞 Contact

For questions and support:
- Create an issue in the GitHub repository
- Contact the maintainers at [email]
- Join our [Discord/Slack] community

---

For more detailed information, check out our [Documentation](docs/README.md).
