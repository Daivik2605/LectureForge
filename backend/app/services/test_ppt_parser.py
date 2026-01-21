from app.services.ppt_parser import parse_ppt

if __name__ == "__main__":
    file_path = "sample.pptx"
    slides = parse_ppt(file_path)
    
    for slide in slides:
        print(slide)
