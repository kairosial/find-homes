import pymupdf4llm
import pandas as pd
import re
import os, time
from io import StringIO
from llama_index.core.schema import Document
from bs4 import BeautifulSoup
from openai import AzureOpenAI
from dotenv import load_dotenv



# pymu
special_chars = ['•', '■', '※']
