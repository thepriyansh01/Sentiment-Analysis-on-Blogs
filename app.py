import re
import os
import math
import requests

import pandas as pd

from bs4 import BeautifulSoup

import nltk
nltk.download('punkt')
from nltk.tokenize import sent_tokenize, word_tokenize
from textstat import syllable_count

from transformers import pipeline
sentiment_analysis_pipeline = pipeline("sentiment-analysis")


df = pd.read_excel('/Output Data Structure.xlsx')


def using_bs(url):
    # Send a GET request to the URL
    response = requests.get(url)
    
    # Check if the request was successful
    if response.status_code == 200:
        # Parse the HTML content of the website
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Extract title
        title_element = soup.find('h1')
        title = title_element.text.strip() if title_element else "Title not found"
        
        # Extract main content paragraph within td-main-content class
        main_content_element = soup.find(class_='td-post-content tagdiv-type')
        main_content = main_content_element.text.strip() if main_content_element else "Main content paragraph not found"
        
        return title, main_content
    else:
        print("Failed to retrieve the website content. Status code:", response.status_code,url)
        return None, None


def process_df(df):
    # Create a folder named 'blog_text' if it doesn't exist
    output_folder = 'blog_text'
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    # Iterate over each row in the DataFrame
    for index, row in df.iterrows():
        link = row['URL']
        
        if(link[-1] == '/'):
          link = link[:-1]
        filename = link.split('/')[-1]
        save_path = os.path.join(output_folder, filename + ".txt")  # Save path with .txt extension

        # Call the function using_bs and save the output to a text file
        title, main_content = using_bs(link)
        if title and main_content:
            with open(save_path, 'w', encoding='utf-8') as f:
                f.write(f"{title}\n\n")
                f.write(f"\n{main_content}")



def analyze_text(text):
    max_tokens = sentiment_analysis_pipeline.tokenizer.model_max_length
    sentiment_scores = {'POSITIVE': 0, 'NEGATIVE': 0}
    num_chunks = math.ceil(len(text) / max_tokens)
    
    for i in range(num_chunks):
        chunk_text = text[i * max_tokens: (i + 1) * max_tokens]
        chunk_sentiment_scores = sentiment_analysis_pipeline(chunk_text)
        
        for score in chunk_sentiment_scores:
            sentiment_scores[score['label']] += score['score']
    
    # Normalize scores by dividing by the number of chunks
    num_chunks = max(num_chunks, 1)  # Ensure at least 1 to avoid division by zero
    positive_score = sentiment_scores['POSITIVE'] / num_chunks
    negative_score = sentiment_scores['NEGATIVE'] / num_chunks
    
    # Other analysis remains the same as before
    sentences = sent_tokenize(text)
    words = word_tokenize(text)
    word_count = len(text)
    avg_sentence_length = sum(len(word_tokenize(sentence)) for sentence in sentences) / len(sentences)
    complex_word_count = sum(syllable_count(word) > 2 for word in words)
    percentage_complex_words = (complex_word_count / word_count) * 100
    fog_index = 0.4 * (avg_sentence_length + percentage_complex_words)
    avg_words_per_sentence = word_count / len(sentences)
    avg_word_length = sum(len(word) for word in words) / word_count
    syllables_per_word = sum(syllable_count(word) for word in words) / word_count
    personal_pronouns = len(re.findall(r'\b(?:i|we|my|ours|us)\b', text, flags=re.IGNORECASE))
    
    
    return {
        'POSITIVE SCORE': positive_score,
        'NEGATIVE SCORE': negative_score,
        'POLARITY SCORE' : (positive_score - negative_score)/ ((positive_score + negative_score) + 0.000001),
        'SUBJECTIVITY SCORE': (positive_score + negative_score)/ ((word_count) + 0.000001),
        'AVG SENTENCE LENGTH': avg_sentence_length,
        'PERCENTAGE OF COMPLEX WORDS': percentage_complex_words,
        'FOG INDEX': fog_index,
        'AVG NUMBER OF WORDS PER SENTENCE': avg_words_per_sentence,
        'COMPLEX WORD COUNT': complex_word_count,
        'WORD COUNT': word_count,
        'SYLLABLE PER WORD': syllables_per_word,
        'PERSONAL PRONOUNS': personal_pronouns,
        'AVG WORD LENGTH': avg_word_length
    }

def analyze_text_files(folder_path, dataFrame):
    # Iterate over each file in the folder
    for file_name in os.listdir(folder_path):
        if file_name.endswith(".txt"):
            file_path = os.path.join(folder_path, file_name)

            # Open the text file and read its contents
            with open(file_path, 'r', encoding='utf-8') as file:
                text = file.read()

            # Apply the analyze_text function to the text
            analysis = analyze_text(text)
            for key, value in analysis.items():
                # Update the DataFrame with the analysis results
                url = "https://insights.blackcoffer.com/" + os.path.splitext(file_name)[0] + "/"
                dataFrame.loc[df['URL'] == url, key] = value


process_df(df)
newDF = df
analyze_text_files('/content/blog_text', newDF)
newDF.to_excel('final.xlsx', index=False)