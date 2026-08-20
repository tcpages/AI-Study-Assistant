#Import statements

import streamlit as strm
import os
from pypdf import PdfReader
import docx
from openai import OpenAI
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
import io
from PIL import Image


#Variable initialization
pgIcon = Image.open("pgicon1.jpeg")

#Layout

strm.set_page_config(page_title="T's AI Study Assistant", page_icon=pgIcon, layout="wide", initial_sidebar_state="expanded", menu_items={'About': "# This is a platform where you can use OpenAI to efficiently study!", 'Get Help': 'https://platform.openai.com'})


#API Key

apiKey = os.getenv("OPENAI_API_KEY")

if not apiKey:
	strm.sidebar.title(":blue[**API Key:**]")
	apiKey = strm.sidebar.text_input("Please enter full API Key here:", type="password", autocomplete="off", help="Get a key from https://platform.openai.com")
	if not apiKey:
		strm.info(":red[** Please enter your OPENAI API Key in the sidebar to begin.**]")

#Info Tab on the left
strm.sidebar.title(":blue[**How To Use This App**]")
strm.sidebar.write("\n On the left hand side upload notes or even the content of your choice and get key concepts/vocab and even generate a study guide \n\n")
strm.sidebar.write("\n On the right hand side upload all your assignments and their corresponding due dates to organize them and download it all at once.")

client = OpenAI(api_key=apiKey) if apiKey else None


#Key function

def extract_text_from_pdf(file):
	reader = PdfReader(file)
	text = ""
	for page in reader.pages:
		text += page.extract_text() + "\n"
	return text

def extract_text_from_docx(file):
    	doc = docx.Document(file)
    	return "\n".join([p.text for p in doc.paragraphs])

def generate_pdf_bytes(text_content):
  pdf_buffer = io.BytesIO()
  doc = SimpleDocTemplate(pdf_buffer, pagesize=letter, title="Tailored Study Guide")
  styles = getSampleStyleSheet()

  
  body_style = ParagraphStyle(
      'theStyle',
      parent=styles['BodyText'], 
      fontSize=12, 
      leading=16, 
      textColor=colors.HexColor('#222222'))


  story = []
  paragraphs = text_content.split('\n\n')
  for para in paragraphs:
    if para.strip():
      formatted_text = para.replace('\n', '<br/>')
      story.append(Paragraph(formatted_text, body_style))
      story.append(Spacer(1, 12))  


  doc.build(story)
  pdf_buffer.seek(0)
  return pdf_buffer


#User Interface

strm.title(":blue[T's AI Study Assistant: Generate a study guide, get key concepts, and create a printable calendar]")
strm.write("Submit notes or chapters to highlight and list key concepts and generate a study guide for review. Submit additional due date with assignments to get a printable planner with each date included.")


#Layout for Inputs

col1, col2 = strm.columns(2)

with col1:
    strm.subheader("1. Content Highlights and Guide")
    givenNotes = strm.file_uploader("Upload your Lecture Notes (PDF or DOCX)", type=["pdf", "docx"])
    
    #Button to execute key concepts and its execution
    if strm.button("Click Here To Go Through Key Concepts"):
        if not client:
            strm.error("API client unable to initialize. Please provide a valid OpenAI API Key.")
        elif not givenNotes:
            strm.error("Please upload your study material.")
        else:
            with strm.spinner("Processing data, please wait a moment..."):
                try:
                    file_ext = givenNotes.name.split(".")[-1]
                    if file_ext == "pdf":
                        notes_text = extract_text_from_pdf(givenNotes)
                    else:
                        notes_text = extract_text_from_docx(givenNotes)

                    contextInfo = f"StudyMaterial:\n{notes_text}"

                    with strm.spinner("Analyzing keywords and concepts..."):
                        thePrompt = (
                            "You are an expert at summarization and analyzing key concepts and vocabulary. "
                            "Find important vocabulary and concepts. Provide your output in exactly "
                            "two sections, separated by a line and a '***'. \n\n"
                            "Section 1: Clear bullet points of important vocabulary found in the provided document"
                            "and its associated defintion. \n"
                            "Section 2: Clear bullet points of key concepts found in the provided document.")

                        theResponse = client.chat.completions.create(
                            model="gpt-4o-mini",
                            messages=[
                                {"role": "system", "content": thePrompt},
                                {"role": "user", "content": notes_text}
                            ],
                            temperature=0.3 )

                        strm.session_state['theAnalysis'] = theResponse.choices[0].message.content


                    #For generating a study guide
                    with strm.spinner("Generating your study guide..."):
                        system_prompt = f"""
                        You are a study guide generator. Your job is to make notes based on the Material uploaded.
                        The study guide should be clear and organized and in a pdf format. Use on the information
                        contained in the document. The study guide should go through key concepts, important ideas
                        and relationships, and important vocabulary. The final page of the study guide should include
                        a flashcard review page with the important vocabulary and each of its associated definition.
                        """

                        response = client.chat.completions.create(
                            model="gpt-4o-mini",
                            messages=[
                                {"role": "system", "content": thePrompt},
                                {"role": "user", "content": notes_text}
                            ],
                            temperature=0.7)

                        strm.session_state['generated_guide'] = response.choices[0].message.content
                            
        

                except Exception as e:
                    strm.error(f"An error occurred while processing: {e}")


    #Output for Key concepts
    if 'theAnalysis' in strm.session_state:
        strm.markdown(" *** ")
        strm.header("Key Concepts and Highlights")
        strm.info(" Use the information below to carefully understand important concepts from the material!")

        theParts = strm.session_state['theAnalysis'].split('---')
        
        col_matched, col_missed = strm.columns(2)

        with col_matched:
            strm.subheader(":blue[Important Vocabulary]")
            if len(theParts) > 0:
                vocab = theParts[0].replace("Section 1:", "").strip()
                strm.markdown(vocab)

        with col_missed:
            strm.subheader(":blue[Key Concepts]")
            if len(theParts) > 1:
                keyConcepts = theParts[1].replace("Section 2:", "").strip()
                strm.markdown(keyConcepts)    


    #Output for Generated Study Guide
    if 'generated_guide' in strm.session_state:
        strm.markdown(" *** ")
        strm.header(" :blue[Generated Study Guide]")

        preview = strm.text_area("Review & Study with Guide Below", value=strm.session_state['generated_guide'], height=350)
        pdfInfo = generate_pdf_bytes(preview)

        strm.download_button(
            label="Click Here to Download as a PDF",
            data=pdfInfo,
            file_name="StudyGuide.pdf",
            mime="application/pdf")
           

#Planner Feature

with col2:

    strm.subheader("2. Organize your Assignments in a Calendar")
    uploadedDates = strm.file_uploader("Upload a list of your assignments and their associated due dates (PDF or DOCX)", type=["pdf", "docx"])
    
#Button for Calendar and its execution
    if strm.button("Click Here To Organize your Assignment List"):
        if not client:
            strm.error("API client unable to initialize. Please provide a valid OpenAI API Key.")
        elif not uploadedDates:
            strm.error("Please upload your assignment names with their due dates.")
        else:
            with strm.spinner("Processing data..."):
                try:
                    fileEx = uploadedDates.name.split(".")[-1]
                    if fileEx == "pdf":
                        AssignDate = extract_text_from_pdf(uploadedDates)
                    else:
                        AssignDate = extract_text_from_docx(uploadedDates)
                    
                    dateData = f"ASSIGNMENT:\n{AssignDate}"

                    with strm.spinner("Analyzing dates..."):
                        systemPrompt = f"""
                        You are an expert calendar assistant. Organize the provided assignments according to its
                        corresponding due dates and importance. Create a calendar and fill it with each assignment.
                        """

                        res = client.chat.completions.create(
                            model="gpt-4o-mini",
                            messages=[
                                {"role": "system", "content": systemPrompt},
                                {"role": "user", "content": dateData}
                            ],
                            temperature=0.7 )

                        strm.session_state['generatedCalendar'] = res.choices[0].message.content
                            

                except Exception as e:
                    strm.error(f"An error occurred while processing: {e}")


    #Output to be displayed
    if 'generatedCalendar' in strm.session_state:
        strm.markdown("---")
        strm.header(" :blue[Generated Assignment Calendar]")

        cal = strm.text_area("Review & Use Calendar Below", value=strm.session_state['generatedCalendar'], height=350)
        pdfCal = generate_pdf_bytes(cal)

        strm.download_button(
            label="Click Here to Download as a PDF",
            data=pdfCal,
            file_name="AssignmentCalendar.pdf",
            mime="application/pdf")









































