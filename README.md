# Ask my PDF



Thank you for your interest in my application. Please be aware that this is only a **Proof of Concept system** and may contain bugs or unfinished features. If you like this app you can ❤️ [follow me](https://twitter.com/KerbalFPV) on Twitter for news and updates.



### Ask my PDF - Question answering system built on top of GPT3

The main use case is answering questions about boardgame rules based on the instruction manual. The app can be used for many other tasks but this particular one is a) very close to me as I'm a big fan of boardgames, b) rather harmless in the case of LLM's halucinations.  



🌐 The app can be accessed in the Streamlit Community Cloud (https://ask-my-pdf.streamlit.app/) but it requires your own [OpenAI's API key](https://platform.openai.com/account/api-keys).



📄 The system implements the following papers:

- [In-Context Retrieval-Augmented Language Models](https://arxiv.org/abs/2302.00083) aka **RALM**

- [Precise Zero-Shot Dense Retrieval without Relevance Labels](https://arxiv.org/abs/2212.10496) aka **HyDE** (Hypothetical Document Embeddings)



### Diagrams: high-level documentation



#### RALM + HyDE

![RALM + HyDE](docs/ralm_hyde.jpg)



#### RALM + HyDE + context

![RALM + HyDE + context](docs/ralm_hyde_wc.jpg)

