from app.services.qa_chain import qa_chain

if __name__ == "__main__":
    slide_text = """
TOPIC – PHOTOSYNTHESIS
OBJECTIVE – Students will be able to explain the process of photosynthesis
and identify its importance to plant life.
"""

    result = qa_chain.invoke({"slide_text": slide_text})
    print(result)
    
