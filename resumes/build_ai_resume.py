from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable, Table, TableStyle, ListFlowable, ListItem
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY

NAVY = colors.HexColor("#1F3A5F")
F, FB = "Helvetica", "Helvetica-Bold"
name = ParagraphStyle("n", fontName=FB, fontSize=22, leading=26, alignment=TA_CENTER, textColor=NAVY)
role = ParagraphStyle("r", fontName=FB, fontSize=10.5, leading=14, alignment=TA_CENTER, textColor=colors.HexColor("#333333"))
contact = ParagraphStyle("c", fontName=F, fontSize=9, leading=12, alignment=TA_CENTER)
h = ParagraphStyle("h", fontName=FB, fontSize=11, leading=14, textColor=NAVY, spaceBefore=9, spaceAfter=2)
body = ParagraphStyle("b", fontName=F, fontSize=9, leading=12, alignment=TA_JUSTIFY)
bul = ParagraphStyle("bl", parent=body, alignment=0)
proj = ParagraphStyle("p", fontName=F, fontSize=9, leading=12, spaceBefore=5, spaceAfter=1)

def sec(t):
    return [Paragraph(t.upper(), h), HRFlowable(width="100%", thickness=0.8, color=NAVY, spaceAfter=4)]
def bullets(items):
    return ListFlowable([ListItem(Paragraph(i, bul), leftIndent=10, bulletColor=NAVY) for i in items],
        bulletType="bullet", start="•", bulletFontSize=7, leftIndent=10, bulletOffsetY=-0.5)
def pr(title, tools):
    return Paragraph(f"<b>{title}</b> | <i>{tools}</i>", proj)

s = []
s += [Paragraph("ANURAG RAJKUMAR TIWARI", name),
      Paragraph("AI Quality Engineer | Python Test Automation | LLM Evaluation", role),
      Spacer(1,5),
      Paragraph("+91-9653235350 &nbsp;|&nbsp; anuragtiwari.dev1@gmail.com &nbsp;|&nbsp; "
                "<link href='https://github.com/anurag123-at' color='#1F3A5F'>github.com/anurag123-at</link> &nbsp;|&nbsp; "
                "<link href='https://linkedin.com/in/anuragtiwari-dev' color='#1F3A5F'>linkedin.com/in/anuragtiwari-dev</link>", contact)]

s += sec("Summary")
s.append(Paragraph("Final-year B.E. Computer Science student (CGPA 9.20/10) and current AI Engineer Intern, with Python, SQL, AWS and REST API skills, three earlier internships and a deployed freelance project. "
  "Focused on test automation for AI products: LLM evaluation suites (accuracy, groundedness, refusal behaviour), web and API automation, "
  "and quality checks in CI/CD. Comfortable validating data with SQL and judging non-deterministic outputs beyond simple pass/fail.", body))

s += sec("Technical Skills")
rows = [
 ("Programming", "Python (OOP, reusable modules), SQL, JavaScript (ES6+)"),
 ("Test Automation", "Pytest, Playwright, Page Object Model, test strategy and framework design"),
 ("LLM / AI Evaluation", "DeepEval, Ragas, golden datasets, hallucination and groundedness checks, prompt-injection testing"),
 ("API Testing", "REST APIs, Postman, Swagger/OpenAPI, JWT authentication and authorization"),
 ("Data and Databases", "MySQL, SQL, MongoDB, Pandas, NumPy, data cleaning, dataset validation, image annotation (YOLO)"),
 ("Cloud", "AWS: EC2, Security Groups, IAM, S3"),
 ("CI/CD and Tools", "Git, GitHub, GitHub Actions, Linux, Bash scripting, Django, Node.js, Express.js, React.js"),
]
t = Table([[Paragraph(f"<b>{a}</b>", body), Paragraph(b, body)] for a,b in rows], colWidths=[34*mm, None])
t.setStyle(TableStyle([("VALIGN",(0,0),(-1,-1),"TOP"),("LEFTPADDING",(0,0),(-1,-1),0),("RIGHTPADDING",(0,0),(-1,-1),0),
                       ("TOPPADDING",(0,0),(-1,-1),1.5),("BOTTOMPADDING",(0,0),(-1,-1),1.5)]))
s.append(t)

s += sec("Projects")
s.append(pr("LLM Response Evaluation Suite for a RAG Q&amp;A Assistant", "Python, Pytest, DeepEval, Ragas, GitHub Actions"))
s.append(bullets([
 "Automated scoring of answers for accuracy, groundedness, relevance and refusal behaviour against a versioned golden dataset.",
 "Tracked hallucination rate per run; added prompt-injection and PII-leakage cases; enforced score thresholds in CI on every commit."]))
s.append(pr("Web and API Test Automation Framework", "Python, Playwright, Pytest, Postman, Swagger/OpenAPI, GitHub Actions"))
s.append(bullets([
 "Reusable OOP framework (Page Object Model) for end-to-end web tests and REST API validation of schemas, auth and negative cases.",
 "Built API test collections from OpenAPI specs; generated reports and ran the full suite automatically in CI."]))
s.append(pr("Educational Classes Website (Freelance)", "Django, HTML, CSS"))
s.append(bullets(["Delivered, deployed and maintained a production-ready client site with server-side rendering, forms and an admin panel."]))

s += sec("Experience")
s.append(Paragraph("<b>AI Engineer Intern</b>, CMS, Ghansoli <font color='#555555'>(October 2026 – Present)</font>", proj))
s.append(bullets([
 "Annotated images and generated labelled datasets for computer-vision model training.",
 "Trained a YOLO model to auto-annotate new data.",
 "Wrote Python scripts to rename, sort and split labelled files, and to remove duplicates, empty files and images with no matching .txt label."]))
for ttl, org, d, b in [
 ("Python Trainee", "Smartbyte Education", "8 months", "Hands-on Python training covering core programming, problem solving and scripting."),
 ("Data Analytics Intern", "Imarticus Learning", "3 months", "Cleaned, validated and analyzed datasets with Python, Pandas, SQL and Power BI; built dashboards."),
 ("Data Analytics Intern", "TechnoHacks Solutions", "2 months", "Performed data cleaning and exploratory analysis using Pandas, NumPy, Matplotlib and Seaborn.")]:
    s.append(Paragraph(f"<b>{ttl}</b>, {org} <font color='#555555'>({d})</font>", proj))
    s.append(bullets([b]))

s += sec("Education and Certifications")
s.append(bullets([
 "<b>B.E. Computer Science</b>, Terna Engineering College, Mumbai University, 2023–2027, CGPA 9.20/10; HSC (PCMB) 2023: 85%; SSC 2021: 91%",
 "Full Stack Web Development (MERN); Version Control and API Development (Git, REST APIs) — Coursera, Udemy, Simplilearn, Great Learning"]))

doc = SimpleDocTemplate("/tmp/r/Anurag_Tiwari_AI_Quality_Engineer_Resume.pdf", pagesize=A4,
    leftMargin=15*mm, rightMargin=15*mm, topMargin=12*mm, bottomMargin=10*mm,
    title="Anurag Rajkumar Tiwari - Resume", author="Anurag Rajkumar Tiwari")
doc.build(s)
from pypdf import PdfReader
print(len(PdfReader("/tmp/r/Anurag_Tiwari_AI_Quality_Engineer_Resume.pdf").pages))
