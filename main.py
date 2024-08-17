from bs4 import BeautifulSoup
from ebooklib import epub
import os, sys
import subprocess, multiprocessing
import tqdm

proj_name=sys.argv[1]

def clean_string(input_string):
    """
    This function removes all newlines and extra spaces from the input string.
    
    Parameters:
    input_string (str): The string to be cleaned.
    
    Returns:
    str: A cleaned string with no newlines and single spaces between words.
    """
    # Remove newlines
    no_newlines = input_string.replace('\n', ' ')
    
    # Split the string into words and rejoin with a single space
    cleaned_string = ' '.join(no_newlines.split())
    
    return cleaned_string



def divide_str_array(strin,threshold_chars=500):
    arr=strin.split('\n')
    result=[]
    tmp=''
    for i in arr:
        i=i.replace("“","").replace("”","")
        tmp+=i +'。\n'
        if len(tmp) > threshold_chars:
            result.append(tmp)
            tmp=""
    result.append(tmp)
    return result
    

def read_epub(epub_file_path):
    book = epub.read_epub(epub_file_path)
    current_h1 = ""
    chapters = []

    for item in book.get_items():
        # Check if item is of type Chapter
        if isinstance(item, epub.EpubHtml):
            content = item.get_content()
            content = content.decode('utf-8')

            # Use BeautifulSoup to parse HTML
            soup = BeautifulSoup(content, 'html.parser')

            # Extract text content
            text_content = ""
            for tag in soup.find_all(['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6']):
                text_content += tag.get_text() + '。\n'
                
            # Find the first appearance of a heading tag
            chapter_title=""
            first_heading = soup.find(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
            if first_heading:
                if first_heading.name == 'h1':
                    current_h1 = clean_string(first_heading.get_text(strip=True))
                elif first_heading.name == 'h2' and len(current_h1) > 0:
                    chapter_title = current_h1+"--"

                chapter_title += clean_string(first_heading.get_text())
            
            text_content=divide_str_array(text_content)
            
            for idx,paragraph in enumerate(text_content):
                progress=f"[{idx+1}]" if len(text_content)>1 else ""
                chapters.append((item.get_id(), progress+chapter_title, paragraph, soup))
    
    return chapters

def gen_tts(f):
    if not os.path.exists(f"{proj_name}/{f}.mp3"):
        cmd_say=["say","-f",f"{proj_name}/{f}.txt",\
                   "-o",f"{proj_name}/{f}.aiff"]
        subprocess.run(cmd_say)
        cmd_ffmpeg=["ffmpeg","-i",f"{proj_name}/{f}.aiff","-b:a","64k","-ac","1",
                    "-id3v2_version","3","-metadata",f'artist=EPUB',\
                    "-metadata",f'album={proj_name}',\
                    f"{proj_name}/{f}.mp3"]
        subprocess.run(cmd_ffmpeg)
        subprocess.run(["rm",f"{proj_name}/{f}.aiff"])


if __name__ == '__main__':
    
    if os.path.exists(proj_name+".txt"):
        chapters=[]
        with open(proj_name+".txt") as f:
            content=f.read()
            for i in divide_str_array(content):
                chapters.append(("","C",i,None))
        
    else:
        epub_file_path = proj_name+'.epub'
        chapters = read_epub(epub_file_path)
    directory_path=proj_name
    if not os.path.exists(directory_path):
        # If it doesn't exist, create it
        os.mkdir(directory_path)
    cnt=0
    filelist=[]
    for chapter_id, chapter_title, chapter_content,soup in chapters:
        cnt+=1
        chapter_title=chapter_title.replace("/","_")
        filelist.append(f"{cnt:04d}.{chapter_title}")
        path=os.path.join(directory_path,f"{cnt:03d}.{chapter_title}.txt")
        with open(path,"w") as f:
            f.write(chapter_content)

    with multiprocessing.Pool(4) as po:
        res=po.imap(gen_tts,filelist)
        for _ in tqdm.tqdm(res,total=len(filelist)):
            pass
