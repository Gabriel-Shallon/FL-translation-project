import os
import google.generativeai as genai

# Make sure to set your API key as an environment variable
API_KEY = "AIzaSyCP2JQmAuE8gYFRy34FMIRVUZpHQIjxQNw"

if not API_KEY:
    print("ERROR: Google API key not found. Please set the GOOGLE_API_KEY environment variable.")
else:
    genai.configure(api_key=API_KEY)
    print("Available models that support 'generateContent':\n")
    
    for model in genai.list_models():
      # We check if 'generateContent' is a supported method for the model
      if 'generateContent' in model.supported_generation_methods:
        print(model.name)