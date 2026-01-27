from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter

def create_test_pdf(filename):
    c = canvas.Canvas(filename, pagesize=letter)
    width, height = letter

    # --- Page 1: Introduction ---
    c.setFont("Helvetica-Bold", 24)
    c.drawString(100, height - 100, "Lecture 1: The Future of AI")
    
    c.setFont("Helvetica", 12)
    text = [
        "Artificial Intelligence is transforming the world.",
        "In this lecture, we will cover the history of neural networks,",
        "the rise of large language models, and the ethics of automation.",
        "AI is not just about code; it is about mimicking human cognition."
    ]
    y = height - 150
    for line in text:
        c.drawString(100, y, line)
        y -= 20

    c.showPage() # End page 1

    # --- Page 2: Technical Overview ---
    c.setFont("Helvetica-Bold", 18)
    c.drawString(100, height - 100, "Deep Learning and Transformers")
    
    c.setFont("Helvetica", 12)
    text2 = [
        "Transformers use an attention mechanism to weigh the importance of input data.",
        "The 'Attention is All You Need' paper changed natural language processing.",
        "Key components include encoders, decoders, and multi-head attention.",
        "This architecture allows for massive parallelization during training."
    ]
    y = height - 150
    for line in text2:
        c.drawString(100, y, line)
        y -= 20

    c.showPage() # End page 2

    c.save()
    print(f"Success: {filename} created!")

if __name__ == "__main__":
    create_test_pdf("ai_lecture_test.pdf")