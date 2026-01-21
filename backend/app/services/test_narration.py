from app.services.narration_chain import narration_chain

if __name__ == "__main__":
    slide_text = """
TOPIC – CROPPING SEASONS
OBJECTIVE – Students will be able to remember crop types
based on sowing and harvesting time.
"""

    result = narration_chain.invoke({"slide_text": slide_text})
    print(result)
    # Old LangChain LLMChain usage (if needed)
    # result = narration_chain.run(slide_content=slide_text)
    # print(result)
