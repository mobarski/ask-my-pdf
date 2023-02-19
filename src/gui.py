__version__ = "0.3.6"
app_name = "Ask my PDF"


# BOILERPLATE

import streamlit as st
st.set_page_config(layout='centered', page_title=f'{app_name} {__version__}')
ss = st.session_state
if 'debug' not in ss: ss['debug'] = {}
import css
st.write(f'<style>{css.v1}</style>', unsafe_allow_html=True)
header1 = st.empty() # for errors / messages
header2 = st.empty() # for errors / messages
header3 = st.empty() # for errors / messages

# IMPORTS

import prompts
import model

# COMPONENTS

def ui_spacer(n=2, line=False, next_n=0):
	for _ in range(n):
		st.write('')
	if line:
		st.tabs([' '])
	for _ in range(next_n):
		st.write('')

def ui_info():
	st.markdown(f"""
	# Ask my PDF
	version {__version__}
	
	Question answering system built on top of GPT3.
	""")
	ui_spacer(1)
	st.write("Made by [Maciej Obarski](https://www.linkedin.com/in/mobarski/).", unsafe_allow_html=True)
	ui_spacer(1)
	st.markdown("""
		Thank you for your interest in my application.
		Please be aware that this is only a Proof of Concept system
		and may contain bugs or unfinished features.
		If you like this app you can ❤️ [follow me](https://twitter.com/KerbalFPV)
		on Twitter for news and updates.
		""")
	ui_spacer(1)
	st.markdown('Source code can be found [here](https://github.com/mobarski/ask-my-pdf).')

def ui_api_key():
	st.write('## 1. Enter your OpenAI API key')
	def on_change():
		model.use_key(ss['api_key'])
	st.text_input('OpenAI API key', type='password', key='api_key', on_change=on_change, label_visibility="collapsed")

def index_pdf_file():
	if ss['pdf_file']:
		index = model.index_file(ss['pdf_file'], fix_text=ss['fix_text'], frag_size=ss['frag_size'], pg=ss['pg_index'])
		ss['index'] = index
		ss['debug']['n_pages'] = len(index['pages'])
		ss['debug']['n_texts'] = len(index['texts'])
		ss['debug']['pages'] = index['pages']
		ss['debug']['texts'] = index['texts']
		ss['debug']['summary'] = index['summary']

def ui_pdf_file():
	st.write('## 2. Upload your PDF file')
	ss['pg_index'] = st.progress(0)
	disabled = not ss.get('api_key')
	uploaded_file = st.file_uploader('pdf file', type='pdf', key='pdf_file', disabled=disabled, on_change=index_pdf_file, label_visibility="collapsed")

def ui_show_debug():
	st.checkbox('show debug section', key='show_debug')

def ui_fix_text():
	st.checkbox('fix common PDF problems', value=True, key='fix_text')

def ui_temperature():
	#st.slider('temperature', 0.0, 1.0, 0.0, 0.1, key='temperature', format='%0.1f')
	ss['temperature'] = 0.0

def ui_fragments():
	st.number_input('fragment size', 0,2000,200, step=200, key='frag_size')
	st.number_input('max fragments', 1, 10, 4, key='max_frags')


def ui_hyde():
	st.checkbox('use HyDE', value=True, key='use_hyde')

def ui_hyde_summary():
	st.checkbox('use summary in HyDE', value=True, key='use_hyde_summary')

def ui_task_template():
	st.selectbox('task prompt template', prompts.TASK.keys(), key='task_name')

def ui_task():
	x = ss['task_name']
	st.text_area('task prompt', prompts.TASK[x], key='task')

def ui_hyde_prompt():
	st.text_area('HyDE prompt', prompts.HYDE, key='hyde_prompt')

def ui_question():
	st.write('## 3. Ask questions')
	disabled = not ss.get('api_key')
	st.text_area('question', key='question', height=100, placeholder='Enter question here', help='', label_visibility="collapsed", disabled=disabled)

# REF: Hypotetical Document Embeddings
def ui_hyde_answer():
	# TODO: enter or generate
	pass

def ui_output():
	output = ss.get('output','')
	st.markdown(output)

def ui_debug():
	if ss.get('show_debug'):
		st.write('### debug')
		st.write(ss.get('debug',{}))


def b_ask():
	disabled = not ss.get('api_key')
	if st.button('get answer', disabled=disabled, type='primary'):
		text = ss.get('question','')
		temperature = ss.get('temperature', 0.0)
		hyde = ss.get('use_hyde')
		hyde_prompt = ss.get('hyde_prompt')
		if ss.get('use_hyde_summary'):
			summary = ss['index']['summary']
			hyde_prompt += f" Context: {summary}\n\n"
		task = ss.get('task')
		max_frags = ss.get('max_frags',1)
		index = ss.get('index',{})
		with st.spinner('preparing answer'):
			resp = model.query(text, index, task=task, temperature=temperature, hyde=hyde, hyde_prompt=hyde_prompt, max_frags=max_frags, limit=max_frags+2)
		ss['debug']['model.query.resp'] = resp
		
		q = text.strip()
		a = resp['text'].strip()
		output_add(q,a)

def b_clear():
	if st.button('clear output'):
		ss['output'] = ''

def b_reindex():
	if st.button('reindex'):
		index_pdf_file()

def b_reload():
	if st.button('reload prompts'):
		import importlib
		importlib.reload(prompts)

def output_add(q,a):
	if 'output' not in ss: ss['output'] = ''
	new = f'#### {q}\n{a}\n\n'.replace('$',r'\$')
	ss['output'] = new + ss['output']
	print('A:',a,flush=True) # XXX

# LAYOUT

with st.sidebar:
	ui_info()
	ui_spacer(2)
	with st.expander('advanced'):
		ui_show_debug()
		b_clear()
		ui_fragments()
		b_reindex()
		ui_fix_text()
		ui_hyde()
		ui_hyde_summary()
		ui_temperature()
		b_reload()
		ui_task_template()
		ui_task()
		ui_hyde_prompt()

ui_api_key()
ui_pdf_file()
ui_question()
ui_hyde_answer()
b_ask()
ui_output()
ui_debug()
