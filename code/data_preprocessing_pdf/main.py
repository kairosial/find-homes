from pymu import *
from azure_di import *
from table_to_text import *

pdf_name = "LH-25년1차청년매입임대입주자모집공고문(서울지역본부).pdf"
pdf_path = rf"data\pdf\{pdf_name}"
md_file_name = ""
md_file_path = rf"data\markdown\{md_file_name}"

final_text_name = ""
final_text_path = rf"data\text\{final_text_name}"

# [PDF -> Azure DI]



# [PyMuPDF]

# PDF data 추출
llama_reader = pymupdf4llm.LlamaMarkdownReader()
llama_docs = llama_reader.load_data()

# markdown 파일 읽기
with open("document_result.md", "r", encoding="utf-8") as file:
    azure_md = file.read()

# 컬럼 예외처리
cleaned_docs = []
for doc in llama_docs:
    modified = fix_invalid_column_lines(doc.text)
    cleaned_docs.append(Document(text=modified))


# [Azure]

# 페이지 전처리
restructured_pages = azure_md_preprocessing(azure_md)

# Azure DI .md에서 연장표 index 찾기 (반례 가능성 有)
extended_page_list = process_markdown_for_table_groups(azure_md)

# [PyMuPDF]

table_df_list = []

for page_list in extended_page_list:
    full_text = merge_pagetext(cleaned_docs, page_list)
    table_list = extract_combined_tables(full_text)

    # 행이 가장 많은 표 하나만 가져오기
    max_table = max(table_list, key=count_rows)

    # 표 재구성
    merged_table_md = make_merged_table_md(max_table)
    df = make_merged_table_df(merged_table_md)

    target_df = df.ffill(axis=1).ffill(axis=0)
    table_df_list.append(target_df)

# [Azure] - Final
final_md = replace_table_html(restructured_pages, extended_page_list, table_df_list)

# 최종 마크다운 저장
with open("output.md", "w", encoding="utf-8") as f:
    f.write(final_md)


# table -> LLM -> text
process_file(md_file_path, final_text_path)