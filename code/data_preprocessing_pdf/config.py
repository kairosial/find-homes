import pymupdf4llm
import pandas as pd
import re
from io import StringIO
import re
from llama_index.core.schema import Document
from bs4 import BeautifulSoup

# pymu
special_chars = ['•', '■', '※']
