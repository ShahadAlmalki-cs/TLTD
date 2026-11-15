# قالب ملف WSGI لاستضافة PythonAnywhere المجانية.
# انسخي محتواه إلى ملف WSGI من تبويب Web، وبدّلي USERNAME (اسم حسابكِ) والمفتاح السري.
import os, sys
sys.path.insert(0, '/home/USERNAME/tltd')
os.environ['SECRET_KEY'] = 'ضعي-هنا-مفتاحًا-عشوائيًا-طويلًا'
os.environ['DB_PATH'] = '/home/USERNAME/tltd-data/tltd.db'
os.environ['BEHIND_PROXY'] = '1'
from app import app as application
