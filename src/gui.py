__version__ = "0.4.3"
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
import storage
import stats

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
		api_key = ss['api_key']
		model.use_key(api_key)
		if 'data_dict' not in ss: ss['data_dict'] = {} # used only with DictStorage
		ss['storage'] = storage.get_storage(api_key, data_dict=ss['data_dict'])
		ss['debug']['storage.folder'] = ss['storage'].folder
		ss['debug']['storage.class'] = ss['storage'].__class__.__name__
		ss['user'] = ss['storage'].folder # TODO: refactor user 'calculation' from get_storage
		ss['stats'] = stats.get_stats(ss['user'])
	st.text_input('OpenAI API key', type='password', key='api_key', on_change=on_change, label_visibility="collapsed")

def index_pdf_file():
	if ss['pdf_file']:
		ss['filename'] = ss['pdf_file'].name
		index = model.index_file(ss['pdf_file'], fix_text=ss['fix_text'], frag_size=ss['frag_size'], pg=ss['pg_index'])
		usage = index['usage']
		ss['stats'].incr('usage:v1:{date}:{user}',     {'index:'+k:v for k,v in usage.items()})
		ss['stats'].incr('hourly:v1:{date}', {'index:'+k+':{hour}':v for k,v in usage.items()})
		ss['debug']['stats'] = ss['stats'].get('usage:v1:{date}:{user}')
		ss['index'] = index
		debug_index()

def debug_index():
	index = ss['index']
	d = {}
	d['hash'] = index['hash']
	d['frag_size'] = index['frag_size']
	d['n_pages'] = len(index['pages'])
	d['n_texts'] = len(index['texts'])
	d['summary'] = index['summary']
	d['pages'] = index['pages']
	d['texts'] = index['texts']
	ss['debug']['index'] = d

def ui_pdf_file():
	st.write('## 2. Upload or select your PDF file')
	disabled = not ss.get('api_key')
	t1,t2 = st.tabs(['UPLOAD','SELECT'])
	with t1:
		ss['pg_index'] = st.progress(0)
		st.file_uploader('pdf file', type='pdf', key='pdf_file', disabled=disabled, on_change=index_pdf_file, label_visibility="collapsed")
		b_save()
	with t2:
		filenames = ['']
		if ss.get('storage'):
			filenames += ss['storage'].list()
		def on_change():
			name = ss['selected_file']
			if name and ss.get('storage'):
				with ss['spin_select_file']:
					with st.spinner('loading index'):
						index = ss['storage'].get(name)
				ss['filename'] = name # XXX
				ss['index'] = index
				debug_index()
			else:
				ss['index'] = {}
		st.selectbox('select file', filenames, on_change=on_change, key='selected_file', label_visibility="collapsed")
		b_delete()
		ss['spin_select_file'] = st.empty()

def ui_show_debug():
	st.checkbox('show debug section', key='show_debug')

def ui_fix_text():
	st.checkbox('fix common PDF problems', value=True, key='fix_text')

def ui_temperature():
	#st.slider('temperature', 0.0, 1.0, 0.0, 0.1, key='temperature', format='%0.1f')
	ss['temperature'] = 0.0

def ui_fragments():
	#st.number_input('fragment size', 0,2000,200, step=100, key='frag_size')
	st.selectbox('fragment size (characters)', [0,200,300,400,500,600,700,800,900,1000], index=3, key='frag_size')
	b_reindex()
	st.number_input('max fragments', 1, 10, 4, key='max_frags')
	st.number_input('fragments before', 0, 3, 1, key='n_frag_before') # TODO: pass to model
	st.number_input('fragments after',  0, 3, 1, key='n_frag_after')  # TODO: pass to model


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
	disabled = not ss.get('api_key') or not ss.get('index')
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
		n_before = ss.get('n_frag_before',0)
		n_after  = ss.get('n_frag_after',0)
		index = ss.get('index',{})
		with st.spinner('preparing answer'):
			resp = model.query(text, index,
					task=task,
					temperature=temperature,
					hyde=hyde,
					hyde_prompt=hyde_prompt,
					max_frags=max_frags,
					limit=max_frags+2,
					n_before=n_before,
					n_after=n_after,
				)
		usage = resp.get('usage',{})
		usage['cnt'] = 1
		ss['stats'].incr('usage:v1:{date}:{user}',     {'ask:'+k:v for k,v in usage.items()})
		ss['stats'].incr('hourly:v1:{date}', {'ask:'+k+':{hour}':v for k,v in usage.items()})
		ss['debug']['stats'] = ss['stats'].get('usage:v1:{date}:{user}')
		ss['debug']['model.query.resp'] = resp
		ss['debug']['resp.usage'] = usage
		
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

def b_save():
	db = ss.get('storage')
	index = ss.get('index')
	name = ss.get('filename')
	help = "The file will be stored for about 30 days."
	if st.button('save encrypted index in ask-my-pdf', disabled=not db or not index or not name, help=help):
		with st.spinner('saving to ask-my-pdf'):
			db.put(name, index)

def b_delete():
	db = ss.get('storage')
	name = ss.get('selected_file')
	# TODO: confirm delete
	if st.button('delete from ask-my-pdf', disabled=not db or not name):
		with st.spinner('deleting from ask-my-pdf'):
			db.delete(name)
		st.experimental_rerun()

def output_add(q,a):
	if 'output' not in ss: ss['output'] = ''
	new = f'#### {q}\n{a}\n\n'.replace('$',r'\$')
	ss['output'] = new + ss['output']

# LAYOUT

with st.sidebar:
	ui_info()
	ui_spacer(2)
	with st.expander('advanced'):
		ui_show_debug()
		b_clear()
		ui_fragments()
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
