# LlamaLearn Assistant – Enhanced with Flashcards, Streaks & Interactive Analytics
# python -m streamlit run enhanced_aitutor1.py

import streamlit as st
import os
import json
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import random
from groq import Groq
from langchain_community.document_loaders import PyPDFLoader

# Set Groq API Key
os.environ["GROQ_API_KEY"] = "YOUR API KEY"
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# Initialize session state
def init_session():
    if 'login' not in st.session_state:
        st.session_state.login = False
    if 'raw_notes' not in st.session_state:
        st.session_state.raw_notes = ""
    if 'username' not in st.session_state:
        st.session_state.username = ""
    if 'role' not in st.session_state:
        st.session_state.role = ""

# Registration Function
def register():
    st.title("📝 Register New Account")
    new_username = st.text_input("Choose a Username")
    new_password = st.text_input("Choose a Password", type="password")
    confirm_password = st.text_input("Confirm Password", type="password")

    if st.button("Register"):
        if new_password != confirm_password:
            st.error("Passwords do not match.")
            return

        if os.path.exists("users.json"):
            with open("users.json", "r") as f:
                users = json.load(f)
        else:
            users = {}

        if new_username in users:
            st.error("Username already exists.")
        else:
            users[new_username] = {"password": new_password, "role": "student"}
            with open("users.json", "w") as f:
                json.dump(users, f, indent=2)
            st.success("Registration successful! You can now log in.")

# Login Function
def login():
    st.title("📚 LLAMALEARN ASSISTANT")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        if os.path.exists("users.json"):
            with open("users.json", "r") as f:
                users = json.load(f)
        else:
            users = {}

        if username in users and users[username]["password"] == password:
            st.session_state.login = True
            st.session_state.username = username
            st.session_state.role = users[username]["role"]
            st.success(f"Welcome, {username}!")
        else:
            st.error("Invalid credentials")

# Logout Function
def logout():
    if st.sidebar.button("🚪 Logout"):
        st.session_state.login = False
        st.session_state.username = ""
        st.session_state.role = ""
        st.session_state.raw_notes = ""
        st.success("You have been logged out.")

# Profile Display with Streak Info
def show_profile():
    st.sidebar.markdown("---")
    st.sidebar.markdown(f"👤 **User:** {st.session_state.username}")
    st.sidebar.markdown(f"🔑 **Role:** {st.session_state.role.capitalize()}")
    
    # Display streak
    streak = get_user_streak(st.session_state.username)
    if streak > 0:
        st.sidebar.markdown(f"🔥 **Current Streak:** {streak} days")
    else:
        st.sidebar.markdown("🔥 **Start your streak today!**")
    
    st.sidebar.markdown("---")

# Upload Notes
def upload_notes():
    st.header("📤 Upload Your Study Notes")
    uploaded_file = st.file_uploader("Choose a PDF file", type="pdf")
    if uploaded_file:
        with open("temp.pdf", "wb") as f:
            f.write(uploaded_file.read())
        loader = PyPDFLoader("temp.pdf")
        documents = loader.load()
        content = "\n".join([doc.page_content for doc in documents])
        st.session_state.raw_notes = content
        st.success("Notes uploaded successfully!")

# Ask Question Function
def ask_question():
    st.header("🤔 Ask a Question")
    
    if not st.session_state.get("raw_notes"):
        st.warning("⚠️ Please upload your notes first.")
        return
    
    question = st.text_input("Enter your question about the notes:")
    
    if st.button("Get Answer"):
        if question:
            prompt = f"""
            Based on the following notes, please answer this question: {question}
            
            Notes:
            {st.session_state.raw_notes}
            
            Please provide a clear and detailed answer based on the content of the notes.
            """
            
            try:
                response = client.chat.completions.create(
                    messages=[{"role": "user", "content": prompt}],
                    model="llama3-70b-8192"
                )
                
                st.subheader("Answer:")
                st.write(response.choices[0].message.content)
                
            except Exception as e:
                st.error(f"Error generating answer: {str(e)}")
        else:
            st.warning("Please enter a question.")

# Quiz System
# Quiz System
# Fixed Interactive Quiz Function
def interactive_quiz():
    st.header("📋 Interactive Quiz")

    if not st.session_state.get("raw_notes"):
        st.warning("⚠️ Please upload your notes first.")
        return

    # Initialize quiz state
    if "current_question" not in st.session_state:
        st.session_state.current_question = 0
    if "quiz_answers" not in st.session_state:
        st.session_state.quiz_answers = {}
    if "quiz_completed" not in st.session_state:
        st.session_state.quiz_completed = False
    if "quiz_started" not in st.session_state:
        st.session_state.quiz_started = False
    if "quiz_review_mode" not in st.session_state:
        st.session_state.quiz_review_mode = False

    # Quiz settings
    if not st.session_state.quiz_started:
        st.subheader("🎯 Quiz Settings")
        
        col1, col2 = st.columns(2)
        with col1:
            num_questions = st.selectbox("Number of Questions:", [5, 10, 15, 20], index=1)
        with col2:
            quiz_difficulty = st.selectbox("Difficulty Level:", ["mixed", "easy", "medium", "hard"])
        
        quiz_type = st.selectbox("Quiz Type:", ["Multiple Choice", "True/False", "Mixed"])
        
        if st.button("🚀 Start Quiz", type="primary", use_container_width=True):
            st.session_state.quiz_started = True
            st.session_state.current_question = 0  # Ensure it's an integer
            st.session_state.quiz_review_mode = False
            st.session_state.quiz_settings = {
                "num_questions": num_questions,
                "difficulty": quiz_difficulty,
                "type": quiz_type
            }
            generate_quiz_questions()
            st.rerun()
        return

    # Step 1: Generate quiz if not already done
    if "quiz_data" not in st.session_state:
        generate_quiz_questions()

    if not st.session_state.get("quiz_data"):
        st.error("⚠️ Unable to generate quiz questions. Please check your notes or try again.")
        if st.button("🔄 Try Again"):
            st.session_state.quiz_started = False
            st.rerun()
        return

    # Step 2: Display current question (only if not in review mode and not completed)
    if not st.session_state.quiz_completed and not st.session_state.quiz_review_mode and st.session_state.quiz_data:
        current_idx = st.session_state.current_question
        total_questions = len(st.session_state.quiz_data)
        
        # Ensure current_idx is an integer and within bounds
        if not isinstance(current_idx, int) or current_idx >= total_questions:
            st.session_state.current_question = 0
            current_idx = 0
        
        # Progress indicator
        progress = (current_idx + 1) / total_questions
        st.progress(progress)
        
        # Quiz header
        col1, col2, col3 = st.columns([2, 1, 1])
        with col1:
            st.write(f"📊 Question {current_idx + 1} of {total_questions}")
        with col2:
            answered = len([a for a in st.session_state.quiz_answers.values() if a is not None])
            st.write(f"✅ Answered: {answered}")
        with col3:
            time_left = f"⏱️ No time limit"
            st.write(time_left)
        
        # Current question
        q = st.session_state.quiz_data[current_idx]
        
        # Question container with styling
        st.markdown(f"""
        <div style="
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 25px;
            border-radius: 12px;
            margin: 20px 0;
            color: white;
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        ">
            <h3 style="margin-bottom: 15px; color: white;">❓ {q['question']}</h3>
        </div>
        """, unsafe_allow_html=True)
        
        # Answer options based on question type
        if q['type'] == 'multiple_choice':
            # Multiple choice options
            # Calculate the correct index for previously selected option
            selected_index = 0
            if current_idx in st.session_state.quiz_answers:
                user_answer = st.session_state.quiz_answers[current_idx]
                if user_answer in q['options']:
                    selected_index = q['options'].index(user_answer)
            
            selected_option = st.radio(
                "Choose your answer:",
                options=q['options'],
                key=f"q{current_idx}_radio",
                index=selected_index
            )
            
            if selected_option:
                st.session_state.quiz_answers[current_idx] = selected_option
                
        elif q['type'] == 'true_false':
            # True/False options
            # Calculate the correct index for previously selected option
            selected_index = 0
            if current_idx in st.session_state.quiz_answers:
                user_answer = st.session_state.quiz_answers[current_idx]
                if user_answer == "False":
                    selected_index = 1
            
            tf_option = st.radio(
                "Choose your answer:",
                options=["True", "False"],
                key=f"q{current_idx}_tf",
                index=selected_index
            )
            
            if tf_option:
                st.session_state.quiz_answers[current_idx] = tf_option
        
        # Navigation and submission
        col1, col2, col3, col4 = st.columns([1, 1, 1, 1])
        
        with col1:
            if current_idx > 0:
                if st.button("⬅️ Previous"):
                    st.session_state.current_question -= 1
                    st.rerun()
        
        with col2:
            if current_idx < total_questions - 1:
                if st.button("Next ➡️"):
                    st.session_state.current_question += 1
                    st.rerun()
        
        with col3:
            # Jump to question
            selected_q = st.selectbox("Jump to:", range(1, total_questions + 1), 
                                    index=current_idx, key="jump_select")
            if selected_q - 1 != current_idx:
                st.session_state.current_question = selected_q - 1
                st.rerun()
        
        with col4:
            if st.button("📝 Review & Submit", type="primary"):
                st.session_state.quiz_review_mode = True  # Use boolean flag instead of string
                st.rerun()

    # Review screen
    elif st.session_state.quiz_review_mode and not st.session_state.quiz_completed:
        st.subheader("📋 Review Your Answers")
        
        total_questions = len(st.session_state.quiz_data)
        answered_count = len([a for a in st.session_state.quiz_answers.values() if a is not None])
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Total Questions", total_questions)
        with col2:
            st.metric("Answered", f"{answered_count}/{total_questions}")
        
        if answered_count < total_questions:
            st.warning(f"⚠️ You have {total_questions - answered_count} unanswered questions.")
        
        # Show summary of answers
        for idx, q in enumerate(st.session_state.quiz_data):
            answer = st.session_state.quiz_answers.get(idx, "Not answered")
            status = "✅" if idx in st.session_state.quiz_answers else "❌"
            st.write(f"{status} **Q{idx+1}:** {answer}")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("⬅️ Back to Quiz"):
                st.session_state.quiz_review_mode = False
                st.session_state.current_question = 0  # Ensure it's an integer
                st.rerun()
        with col2:
            if st.button("✅ Submit Final Answers", type="primary"):
                st.session_state.quiz_completed = True
                st.session_state.quiz_review_mode = False
                st.rerun()

    # Step 3: Show results after completion
    elif st.session_state.quiz_completed:
        st.subheader("🎉 Quiz Results")
        
        score = 0
        total_questions = len(st.session_state.quiz_data)
        detailed_results = []
        
        for idx, q in enumerate(st.session_state.quiz_data):
            user_ans = st.session_state.quiz_answers.get(idx, "")
            correct_ans = q['correct_answer']
            is_correct = user_ans == correct_ans
            
            if is_correct:
                score += 1
            
            detailed_results.append({
                'question': q['question'],
                'user_answer': user_ans,
                'correct_answer': correct_ans,
                'is_correct': is_correct,
                'explanation': q.get('explanation', 'No explanation available.')
            })
        
        # Final score with visual feedback
        percentage = (score / total_questions) * 100
        
        # Score styling based on performance
        if percentage >= 80:
            score_color = "#28a745"  # Green
            score_emoji = "🎉"
            performance_msg = "Excellent work!"
        elif percentage >= 60:
            score_color = "#ffc107"  # Yellow
            score_emoji = "👍"
            performance_msg = "Good job!"
        else:
            score_color = "#dc3545"  # Red
            score_emoji = "💪"
            performance_msg = "Keep practicing!"
        
        st.markdown(f"""
        <div style="
            background: linear-gradient(135deg, {score_color}20, {score_color}10);
            padding: 30px;
            border-radius: 15px;
            text-align: center;
            border: 2px solid {score_color};
            margin: 20px 0;
        ">
            <h2 style="color: {score_color}; margin-bottom: 10px;">{score_emoji} Your Score: {score}/{total_questions}</h2>
            <h3 style="color: {score_color}; margin-bottom: 10px;">{percentage:.1f}%</h3>
            <p style="color: {score_color}; font-size: 18px;">{performance_msg}</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Detailed results
        st.subheader("📊 Detailed Results")
        
        for idx, result in enumerate(detailed_results, 1):
            with st.expander(f"Question {idx} - {'✅ Correct' if result['is_correct'] else '❌ Incorrect'}"):
                st.write(f"**Question:** {result['question']}")
                st.write(f"**Your Answer:** {result['user_answer']}")
                if not result['is_correct']:
                    st.write(f"**Correct Answer:** {result['correct_answer']}")
                st.write(f"**Explanation:** {result['explanation']}")
        
        # Save quiz results
        save_quiz_results(score, total_questions, percentage, detailed_results)
        
        # Action buttons
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔄 Take New Quiz", use_container_width=True):
                reset_quiz_state()
                st.rerun()
        
        with col2:
            if st.button("📈 View Performance", use_container_width=True):
                st.session_state.redirect_to_performance = True
                st.rerun()

def reset_quiz_state():
    """Reset all quiz-related session state"""
    quiz_keys = ['quiz_data', 'current_question', 'quiz_answers', 'quiz_completed', 
                 'quiz_started', 'quiz_settings', 'quiz_review_mode']
    for key in quiz_keys:
        if key in st.session_state:
            del st.session_state[key]

def generate_quiz_questions():
    """Generate quiz questions based on settings"""
    settings = st.session_state.quiz_settings
    num_questions = settings['num_questions']
    difficulty = settings['difficulty']
    quiz_type = settings['type']
    
    # Create prompt based on quiz type
    if quiz_type == "Multiple Choice":
        type_instruction = "Create only multiple choice questions with 4 options each (A, B, C, D)."
    elif quiz_type == "True/False":
        type_instruction = "Create only True/False questions."
    else:  # Mixed
        type_instruction = "Create a mix of multiple choice (with 4 options A, B, C, D) and True/False questions."
    
    difficulty_instruction = ""
    if difficulty != "mixed":
        difficulty_instruction = f"Make all questions {difficulty} difficulty level."
    
    prompt = f"""
    Generate {num_questions} quiz questions from the following notes.
    {type_instruction}
    {difficulty_instruction}
    
    For each question, provide:
    1. The question text
    2. The options (for multiple choice) or True/False
    3. The correct answer
    4. A brief explanation
    5. Difficulty level (easy/medium/hard)
    
    Format each question as:
    QUESTION: [question text]
    TYPE: [multiple_choice or true_false]
    OPTIONS: [for multiple choice: A. option1, B. option2, C. option3, D. option4]
    CORRECT: [correct answer]
    EXPLANATION: [explanation]
    DIFFICULTY: [easy/medium/hard]
    ---
    
    Notes:
    {st.session_state.raw_notes}
    """
    
    try:
        with st.spinner("🔄 Generating quiz questions..."):
            response = client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model="llama3-70b-8192"
            )
            
            content = response.choices[0].message.content
            questions = []
            
            # Parse the response
            sections = content.split('---')
            for section in sections:
                if 'QUESTION:' in section:
                    lines = section.strip().split('\n')
                    question_data = {}
                    
                    for line in lines:
                        line = line.strip()
                        if line.startswith('QUESTION:'):
                            question_data['question'] = line.replace('QUESTION:', '').strip()
                        elif line.startswith('TYPE:'):
                            question_data['type'] = line.replace('TYPE:', '').strip()
                        elif line.startswith('OPTIONS:'):
                            options_text = line.replace('OPTIONS:', '').strip()
                            # Parse options A. B. C. D.
                            options = []
                            for opt in options_text.split(', '):
                                if '. ' in opt:
                                    options.append(opt.split('. ', 1)[1])
                            question_data['options'] = options
                        elif line.startswith('CORRECT:'):
                            question_data['correct_answer'] = line.replace('CORRECT:', '').strip()
                        elif line.startswith('EXPLANATION:'):
                            question_data['explanation'] = line.replace('EXPLANATION:', '').strip()
                        elif line.startswith('DIFFICULTY:'):
                            question_data['difficulty'] = line.replace('DIFFICULTY:', '').strip()
                    
                    # Validate and add question
                    if 'question' in question_data and 'correct_answer' in question_data:
                        # Set default type if not specified
                        if 'type' not in question_data:
                            question_data['type'] = 'multiple_choice' if 'options' in question_data else 'true_false'
                        
                        # Ensure True/False questions have correct format
                        if question_data['type'] == 'true_false':
                            question_data['options'] = ['True', 'False']
                        
                        questions.append(question_data)
            
            st.session_state.quiz_data = questions[:num_questions]  # Limit to requested number
            
    except Exception as e:
        st.error(f"Error generating quiz: {str(e)}")
        st.session_state.quiz_data = []

def save_quiz_results(score, total, percentage, detailed_results):
    """Save quiz results to learning data"""
    quiz_data = {
        "correct": score,
        "total": total,
        "accuracy": percentage,
        "date": datetime.now().strftime("%Y-%m-%d"),
        "timestamp": datetime.now().isoformat(),
        "activity_type": "quiz",
        "detailed_results": detailed_results
    }
    
    # Load existing data
    if os.path.exists("learning_data.json"):
        with open("learning_data.json", "r") as f:
            data = json.load(f)
    else:
        data = {}
    
    # Add user data
    username = st.session_state.username
    if username not in data:
        data[username] = []
    
    data[username].append(quiz_data)
    
    # Save updated data
    with open("learning_data.json", "w") as f:
        json.dump(data, f, indent=2)

def reset_quiz_state():
    """Reset all quiz-related session state"""
    quiz_keys = ['quiz_data', 'current_question', 'quiz_answers', 'quiz_completed', 
                 'quiz_started', 'quiz_settings']
    for key in quiz_keys:
        if key in st.session_state:
            del st.session_state[key]
def generate_quiz_questions():
    """Generate quiz questions based on settings with improved error handling"""
    settings = st.session_state.quiz_settings
    num_questions = settings['num_questions']
    difficulty = settings['difficulty']
    quiz_type = settings['type']
    
    # Create prompt based on quiz type
    if quiz_type == "Multiple Choice":
        type_instruction = "Create only multiple choice questions with exactly 4 options each."
    elif quiz_type == "True/False":
        type_instruction = "Create only True/False questions."
    else:  # Mixed
        type_instruction = "Create a mix of multiple choice (with exactly 4 options) and True/False questions."
    
    difficulty_instruction = ""
    if difficulty != "mixed":
        difficulty_instruction = f"Make all questions {difficulty} difficulty level."
    
    prompt = f"""
    Generate exactly {num_questions} quiz questions from the following study notes.
    {type_instruction}
    {difficulty_instruction}
    
    IMPORTANT FORMATTING RULES:
    - Use exactly this format for each question
    - Separate each question with "---"
    - For multiple choice, provide exactly 4 options
    - Make questions clear and specific
    
    FORMAT FOR EACH QUESTION:
    QUESTION: [Write a clear question here]
    TYPE: multiple_choice
    OPTION_A: [First option]
    OPTION_B: [Second option] 
    OPTION_C: [Third option]
    OPTION_D: [Fourth option]
    CORRECT: [Write the correct option text exactly as above]
    EXPLANATION: [Brief explanation of why this is correct]
    DIFFICULTY: easy
    ---
    
    OR for True/False:
    QUESTION: [Write a clear true/false statement]
    TYPE: true_false
    CORRECT: True
    EXPLANATION: [Brief explanation]
    DIFFICULTY: medium
    ---
    
    Study Notes:
    {st.session_state.raw_notes[:3000]}
    
    Generate exactly {num_questions} questions following this format precisely.
    """
    
    try:
        with st.spinner("🔄 Generating quiz questions..."):
            response = client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model="llama3-70b-8192",
                temperature=0.7,
                max_tokens=2000
            )
            
            content = response.choices[0].message.content
            st.write("Debug - Raw Response:", content[:500] + "..." if len(content) > 500 else content)  # Debug line
            
            questions = []
            
            # Parse the response
            sections = content.split('---')
            
            for section in sections:
                section = section.strip()
                if not section or 'QUESTION:' not in section:
                    continue
                
                question_data = {}
                lines = section.split('\n')
                
                for line in lines:
                    line = line.strip()
                    if line.startswith('QUESTION:'):
                        question_data['question'] = line.replace('QUESTION:', '').strip()
                    elif line.startswith('TYPE:'):
                        question_data['type'] = line.replace('TYPE:', '').strip()
                    elif line.startswith('OPTION_A:'):
                        if 'options' not in question_data:
                            question_data['options'] = []
                        question_data['options'].append(line.replace('OPTION_A:', '').strip())
                    elif line.startswith('OPTION_B:'):
                        if 'options' not in question_data:
                            question_data['options'] = []
                        question_data['options'].append(line.replace('OPTION_B:', '').strip())
                    elif line.startswith('OPTION_C:'):
                        if 'options' not in question_data:
                            question_data['options'] = []
                        question_data['options'].append(line.replace('OPTION_C:', '').strip())
                    elif line.startswith('OPTION_D:'):
                        if 'options' not in question_data:
                            question_data['options'] = []
                        question_data['options'].append(line.replace('OPTION_D:', '').strip())
                    elif line.startswith('CORRECT:'):
                        question_data['correct_answer'] = line.replace('CORRECT:', '').strip()
                    elif line.startswith('EXPLANATION:'):
                        question_data['explanation'] = line.replace('EXPLANATION:', '').strip()
                    elif line.startswith('DIFFICULTY:'):
                        question_data['difficulty'] = line.replace('DIFFICULTY:', '').strip().lower()
                
                # Validate and clean up question data
                if 'question' in question_data and 'correct_answer' in question_data:
                    # Set default values
                    if 'type' not in question_data:
                        question_data['type'] = 'multiple_choice' if 'options' in question_data else 'true_false'
                    
                    if 'difficulty' not in question_data:
                        question_data['difficulty'] = 'medium'
                    
                    if 'explanation' not in question_data:
                        question_data['explanation'] = 'No explanation provided.'
                    
                    # Handle True/False questions
                    if question_data['type'] == 'true_false':
                        question_data['options'] = ['True', 'False']
                        # Ensure correct answer is properly formatted
                        if question_data['correct_answer'].lower() in ['true', 't', 'yes', '1']:
                            question_data['correct_answer'] = 'True'
                        else:
                            question_data['correct_answer'] = 'False'
                    
                    # Validate multiple choice questions
                    elif question_data['type'] == 'multiple_choice':
                        if 'options' not in question_data or len(question_data['options']) < 2:
                            # Skip invalid multiple choice questions
                            continue
                        
                        # Ensure we have exactly 4 options for consistency
                        while len(question_data['options']) < 4:
                            question_data['options'].append("Not applicable")
                        
                        # Make sure correct answer matches one of the options
                        correct = question_data['correct_answer']
                        if correct not in question_data['options']:
                            # Try to find a close match
                            for option in question_data['options']:
                                if correct.lower() in option.lower() or option.lower() in correct.lower():
                                    question_data['correct_answer'] = option
                                    break
                            else:
                                # If no match found, use first option
                                question_data['correct_answer'] = question_data['options'][0]
                    
                    questions.append(question_data)
            
            # If we don't have enough questions, create some fallback ones
            if len(questions) < 3:
                st.warning("Generated questions were insufficient. Creating fallback questions...")
                questions = create_fallback_questions(num_questions)
            
            st.session_state.quiz_data = questions[:num_questions]
            st.success(f"Successfully generated {len(st.session_state.quiz_data)} questions!")
            
    except Exception as e:
        st.error(f"Error generating quiz: {str(e)}")
        st.info("Creating fallback questions from your notes...")
        st.session_state.quiz_data = create_fallback_questions(num_questions)

def create_fallback_questions(num_questions):
    """Create simple fallback questions when AI generation fails"""
    fallback_questions = []
    
    # Extract some text from notes for basic questions
    notes_text = st.session_state.raw_notes
    sentences = [s.strip() for s in notes_text.split('.') if len(s.strip()) > 20][:num_questions*2]
    
    for i in range(min(num_questions, len(sentences))):
        sentence = sentences[i]
        
        if i % 2 == 0:  # Multiple choice question
            question = {
                'question': f"What is mentioned in the following context: '{sentence[:100]}...'?",
                'type': 'multiple_choice',
                'options': [
                    "This statement is directly mentioned in the notes",
                    "This statement is not in the notes", 
                    "This statement is partially mentioned",
                    "This statement needs clarification"
                ],
                'correct_answer': "This statement is directly mentioned in the notes",
                'explanation': "This information is found in your study notes.",
                'difficulty': 'easy'
            }
        else:  # True/False question
            question = {
                'question': f"True or False: The following information is covered in your notes: '{sentence[:100]}...'",
                'type': 'true_false',
                'options': ['True', 'False'],
                'correct_answer': 'True',
                'explanation': "This information appears in your study materials.",
                'difficulty': 'easy'
            }
        
        fallback_questions.append(question)
    
    # If still not enough, add some generic questions
    while len(fallback_questions) < num_questions:
        fallback_questions.append({
            'question': f"Based on your study notes, which approach is most important for learning?",
            'type': 'multiple_choice',
            'options': [
                "Regular practice and review",
                "Memorizing everything at once",
                "Avoiding difficult topics",
                "Studying only before exams"
            ],
            'correct_answer': "Regular practice and review",
            'explanation': "Consistent practice and review is key to effective learning.",
            'difficulty': 'medium'
        })
    
    return fallback_questions[:num_questions]

# Also add this improved error handling to the quiz display
def display_current_question():
    """Display the current quiz question with better error handling"""
    if not st.session_state.get("quiz_data"):
        st.error("No quiz questions available. Please try generating the quiz again.")
        if st.button("🔄 Regenerate Quiz"):
            if 'quiz_data' in st.session_state:
                del st.session_state.quiz_data
            generate_quiz_questions()
            st.rerun()
        return False
    
    current_idx = st.session_state.current_question
    if current_idx >= len(st.session_state.quiz_data):
        st.error("Question index out of range. Resetting to first question.")
        st.session_state.current_question = 0
        st.rerun()
        return False
    
    return True

def save_quiz_results(score, total, percentage, detailed_results):
    """Save quiz results to learning data"""
    quiz_data = {
        "correct": score,
        "total": total,
        "accuracy": percentage,
        "date": datetime.now().strftime("%Y-%m-%d"),
        "timestamp": datetime.now().isoformat(),
        "activity_type": "quiz",
        "detailed_results": detailed_results
    }
    
    # Load existing data
    if os.path.exists("learning_data.json"):
        with open("learning_data.json", "r") as f:
            data = json.load(f)
    else:
        data = {}
    
    # Add user data
    username = st.session_state.username
    if username not in data:
        data[username] = []
    
    data[username].append(quiz_data)
    
    # Save updated data
    with open("learning_data.json", "w") as f:
        json.dump(data, f, indent=2)

def reset_quiz_state():
    """Reset all quiz-related session state"""
    quiz_keys = ['quiz_data', 'current_question', 'quiz_answers', 'quiz_completed', 
                 'quiz_started', 'quiz_settings']
    for key in quiz_keys:
        if key in st.session_state:
            del st.session_state[key]

# Flashcard System
def flashcard_learning():
    st.header("🃏 Interactive Flashcards")
    
    if not st.session_state.get("raw_notes"):
        st.warning("⚠️ Please upload your notes first.")
        return
    
    # Initialize flashcard session
    if "flashcards" not in st.session_state:
        st.session_state.flashcards = []
        st.session_state.current_card = 0
        st.session_state.card_flipped = False
        st.session_state.session_correct = 0
        st.session_state.session_total = 0
        st.session_state.difficulty_mode = "mixed"
    
    # Generate flashcards if not already done
    if not st.session_state.flashcards:
        with st.spinner("🔄 Generating flashcards from your notes..."):
            generate_flashcards()
    
    if not st.session_state.flashcards:
        st.error("Unable to generate flashcards. Please check your notes.")
        return
    
    # Display session stats
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("📊 Session Progress", f"{st.session_state.session_total} cards")
    with col2:
        accuracy = (st.session_state.session_correct / max(st.session_state.session_total, 1)) * 100
        st.metric("🎯 Accuracy", f"{accuracy:.1f}%")
    with col3:
        total_cards = len(st.session_state.flashcards)
        st.metric("📚 Total Cards", total_cards)
    with col4:
        streak = get_user_streak(st.session_state.username)
        st.metric("🔥 Streak", f"{streak} days")
    
    # Difficulty selector
    difficulty = st.selectbox(
        "Choose difficulty level:",
        ["easy", "medium", "hard", "mixed"],
        index=["easy", "medium", "hard", "mixed"].index(st.session_state.difficulty_mode)
    )
    st.session_state.difficulty_mode = difficulty
    
    # Filter cards by difficulty
    filtered_cards = filter_cards_by_difficulty(st.session_state.flashcards, difficulty)
    
    if not filtered_cards:
        st.warning("No cards available for this difficulty level.")
        return
    
    # Current card
    current_card = filtered_cards[st.session_state.current_card % len(filtered_cards)]
    
    # Card display
    st.markdown("---")
    card_container = st.container()
    
    with card_container:
        if not st.session_state.card_flipped:
            # Show question side
            st.markdown(f"""
            <div style="
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                padding: 40px;
                border-radius: 15px;
                color: white;
                text-align: center;
                font-size: 18px;
                min-height: 200px;
                display: flex;
                align-items: center;
                justify-content: center;
                box-shadow: 0 8px 32px rgba(0,0,0,0.1);
            ">
                <div>
                    <h3 style="margin-bottom: 20px;">❓ Question</h3>
                    <p style="font-size: 20px; line-height: 1.5;">{current_card['question']}</p>
                </div>
            </div>
            """, unsafe_allow_html=True)
        else:
            # Show answer side
            st.markdown(f"""
            <div style="
                background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
                padding: 40px;
                border-radius: 15px;
                color: white;
                text-align: center;
                font-size: 18px;
                min-height: 200px;
                display: flex;
                align-items: center;
                justify-content: center;
                box-shadow: 0 8px 32px rgba(0,0,0,0.1);
            ">
                <div>
                    <h3 style="margin-bottom: 20px;">✅ Answer</h3>
                    <p style="font-size: 20px; line-height: 1.5;">{current_card['answer']}</p>
                </div>
            </div>
            """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Card controls
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        if not st.session_state.card_flipped:
            if st.button("🔄 Flip Card", use_container_width=True, type="primary"):
                st.session_state.card_flipped = True
                st.rerun()
        else:
            # Feedback buttons
            col_a, col_b = st.columns(2)
            with col_a:
                if st.button("❌ Hard", use_container_width=True):
                    record_flashcard_attempt(False, current_card['difficulty'])
                    next_card()
            with col_b:
                if st.button("✅ Easy", use_container_width=True):
                    record_flashcard_attempt(True, current_card['difficulty'])
                    next_card()
    
    # Navigation
    col1, col2, col3 = st.columns([1, 1, 1])
    with col1:
        if st.button("⏮️ Previous"):
            st.session_state.current_card = (st.session_state.current_card - 1) % len(filtered_cards)
            st.session_state.card_flipped = False
            st.rerun()
    
    with col3:
        if st.button("⏭️ Next"):
            next_card()
    
    # End session button
    if st.button("🏁 End Session", type="secondary"):
        save_flashcard_session()
        st.success("Session saved! Great job studying! 🎉")
        # Reset session
        for key in ['flashcards', 'current_card', 'card_flipped', 'session_correct', 'session_total']:
            if key in st.session_state:
                del st.session_state[key]
        st.rerun()

def generate_flashcards():
    """Generate flashcards from notes using Groq"""
    prompt = f"""
    Create 20 educational flashcards from the following notes. Each flashcard should have:
    1. A clear question
    2. A concise answer
    3. A difficulty level (easy, medium, hard)
    
    Format each flashcard as:
    QUESTION: [question text]
    ANSWER: [answer text]
    DIFFICULTY: [easy/medium/hard]
    ---
    
    Make questions varied - include definitions, explanations, examples, and application questions.
    
    Notes:
    {st.session_state.raw_notes}
    """
    
    try:
        response = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama3-70b-8192"
        )
        
        content = response.choices[0].message.content
        cards = []
        
        # Parse the response
        sections = content.split('---')
        for section in sections:
            if 'QUESTION:' in section and 'ANSWER:' in section and 'DIFFICULTY:' in section:
                lines = section.strip().split('\n')
                question = ""
                answer = ""
                difficulty = "medium"
                
                for line in lines:
                    if line.startswith('QUESTION:'):
                        question = line.replace('QUESTION:', '').strip()
                    elif line.startswith('ANSWER:'):
                        answer = line.replace('ANSWER:', '').strip()
                    elif line.startswith('DIFFICULTY:'):
                        difficulty = line.replace('DIFFICULTY:', '').strip().lower()
                
                if question and answer:
                    cards.append({
                        'question': question,
                        'answer': answer,
                        'difficulty': difficulty if difficulty in ['easy', 'medium', 'hard'] else 'medium'
                    })
        
        st.session_state.flashcards = cards
        
    except Exception as e:
        st.error(f"Error generating flashcards: {str(e)}")

def filter_cards_by_difficulty(cards, difficulty):
    """Filter flashcards by difficulty level"""
    if difficulty == "mixed":
        return cards
    return [card for card in cards if card['difficulty'] == difficulty]

def next_card():
    """Move to next card and reset flip state"""
    st.session_state.current_card += 1
    st.session_state.card_flipped = False
    st.rerun()

def record_flashcard_attempt(correct, difficulty):
    """Record the result of a flashcard attempt"""
    st.session_state.session_total += 1
    if correct:
        st.session_state.session_correct += 1

def save_flashcard_session():
    """Save flashcard session data"""
    if st.session_state.session_total == 0:
        return
    
    session_data = {
        "correct": st.session_state.session_correct,
        "total": st.session_state.session_total,
        "accuracy": (st.session_state.session_correct / st.session_state.session_total) * 100,
        "date": datetime.now().strftime("%Y-%m-%d"),
        "timestamp": datetime.now().isoformat(),
        "activity_type": "flashcards"
    }
    
    # Load existing data
    if os.path.exists("learning_data.json"):
        with open("learning_data.json", "r") as f:
            data = json.load(f)
    else:
        data = {}
    
    # Add user data
    username = st.session_state.username
    if username not in data:
        data[username] = []
    
    data[username].append(session_data)
    
    # Save updated data
    with open("learning_data.json", "w") as f:
        json.dump(data, f, indent=2)

def get_user_streak(username):
    """Calculate user's current learning streak"""
    if not os.path.exists("learning_data.json"):
        return 0
    
    with open("learning_data.json", "r") as f:
        data = json.load(f)
    
    if username not in data:
        return 0
    
    # Get unique dates when user studied
    study_dates = set()
    for session in data[username]:
        study_dates.add(session['date'])
    
    # Calculate streak
    current_date = datetime.now().date()
    streak = 0
    
    for i in range(365):  # Check last 365 days
        check_date = current_date - timedelta(days=i)
        date_str = check_date.strftime("%Y-%m-%d")
        
        if date_str in study_dates:
            streak += 1
        else:
            break
    
    return streak

# Enhanced Performance Tracking
def performance():
    st.header("📈 Your Learning Analytics")
    
    if not os.path.exists("learning_data.json"):
        st.info("No performance data yet. Start learning to see your progress!")
        return
    
    with open("learning_data.json", "r") as f:
        data = json.load(f)
    
    username = st.session_state.username
    
    if username not in data or not data[username]:
        st.info("You haven't completed any learning sessions yet.")
        return
    
    user_data = data[username]
    df = pd.DataFrame(user_data)
    df['date'] = pd.to_datetime(df['date'])
    
    # Overall Stats
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        total_sessions = len(user_data)
        st.metric("📚 Total Sessions", total_sessions)
    
    with col2:
        avg_accuracy = df['accuracy'].mean()
        st.metric("🎯 Average Accuracy", f"{avg_accuracy:.1f}%")
    
    with col3:
        streak = get_user_streak(username)
        st.metric("🔥 Current Streak", f"{streak} days")
    
    with col4:
        # Count different activity types
        quiz_sessions = len([s for s in user_data if s.get('activity_type') == 'quiz'])
        flashcard_sessions = len([s for s in user_data if s.get('activity_type') == 'flashcards'])
        st.metric("📊 Quiz/Cards", f"{quiz_sessions}/{flashcard_sessions}")
    
    # Progress Chart
    st.subheader("📊 Learning Progress Over Time")
    
    # Group by date and calculate daily accuracy
    daily_stats = df.groupby('date').agg({
        'accuracy': 'mean',
        'total': 'sum',
        'correct': 'sum'
    }).reset_index()
    
    fig = px.line(daily_stats, x='date', y='accuracy', 
                  title='Daily Learning Accuracy',
                  labels={'accuracy': 'Accuracy (%)', 'date': 'Date'})
    fig.update_layout(showlegend=False)
    st.plotly_chart(fig, use_container_width=True)
    
    # Activity Heatmap
    st.subheader("🗓️ Study Activity Heatmap")
    
    # Create a date range for the last 90 days
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=89)
    date_range = pd.date_range(start_date, end_date, freq='D')
    
    # Count sessions per day
    daily_sessions = df.groupby(df['date'].dt.date).size().reindex(
        date_range.date, fill_value=0
    )
    
    # Create heatmap data
    heatmap_data = []
    for i, date in enumerate(date_range):
        week = i // 7
        day_of_week = date.dayofweek
        sessions = daily_sessions.iloc[i]
        heatmap_data.append({
            'week': week,
            'day': day_of_week,
            'date': date.strftime('%Y-%m-%d'),
            'sessions': sessions
        })
    
    heatmap_df = pd.DataFrame(heatmap_data)
    
    fig = px.density_heatmap(
        heatmap_df, x='week', y='day', z='sessions',
        title='Study Activity (Last 90 Days)',
        labels={'sessions': 'Sessions', 'week': 'Week', 'day': 'Day of Week'},
        color_continuous_scale='Greens'
    )
    
    # Update y-axis labels to show day names
    fig.update_layout(
        yaxis=dict(
            tickmode='array',
            tickvals=[0, 1, 2, 3, 4, 5, 6],
            ticktext=['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
        )
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Recent Sessions
    st.subheader("📝 Recent Learning Sessions")
    recent_sessions = user_data[-10:]  # Last 10 sessions
    
    for session in reversed(recent_sessions):
        accuracy = session['accuracy']
        date = session['date']
        correct = session['correct']
        total = session['total']
        activity_type = session.get('activity_type', 'unknown')
        
        # Color code based on accuracy
        if accuracy >= 80:
            color = "🟢"
        elif accuracy >= 60:
            color = "🟡"
        else:
            color = "🔴"
        
        # Activity icon
        icon = "📋" if activity_type == 'quiz' else "🃏" if activity_type == 'flashcards' else "📚"
        
        st.write(f"{color} {icon} {date}: {correct}/{total} correct ({accuracy:.1f}%) - {activity_type.title()}")

# Interactive Leaderboard
def leaderboard():
    st.header("🏆 Interactive Leaderboard")
    
    if not os.path.exists("learning_data.json"):
        st.info("No leaderboard data available yet.")
        return
    
    with open("learning_data.json", "r") as f:
        data = json.load(f)
    
    if not data:
        st.info("No users have completed learning sessions yet.")
        return
    
    # Calculate stats for each user
    leaderboard_data = []
    
    for username, sessions in data.items():
        if not sessions:
            continue
            
        df = pd.DataFrame(sessions)
        
        total_sessions = len(sessions)
        avg_accuracy = df['accuracy'].mean()
        total_cards = df['total'].sum()
        streak = get_user_streak(username)
        last_activity = max(sessions, key=lambda x: x['timestamp'])['date']
        
        leaderboard_data.append({
            'username': username,
            'total_sessions': total_sessions,
            'avg_accuracy': avg_accuracy,
            'total_cards': total_cards,
            'streak': streak,
            'last_activity': last_activity,
            'score': avg_accuracy * 0.4 + total_sessions * 2 + streak * 5  # Composite score
        })
    
    leaderboard_df = pd.DataFrame(leaderboard_data)
    leaderboard_df = leaderboard_df.sort_values('score', ascending=False)
    
    # Leaderboard tabs
    tab1, tab2, tab3 = st.tabs(["🏆 Overall Rankings", "📊 Comparison Charts", "🔥 Streak Leaders"])
    
    with tab1:
        st.subheader("Top Learners")
        
        for i, (_, row) in enumerate(leaderboard_df.head(10).iterrows(), 1):
            # Medal emojis for top 3
            if i == 1:
                medal = "🥇"
            elif i == 2:
                medal = "🥈" 
            elif i == 3:
                medal = "🥉"
            else:
                medal = f"{i}."
            
            col1, col2, col3, col4, col5 = st.columns([1, 3, 2, 2, 2])
            
            with col1:
                st.write(medal)
            with col2:
                st.write(f"**{row['username']}**")
            with col3:
                st.write(f"{row['avg_accuracy']:.1f}% avg")
            with col4:
                st.write(f"{row['total_sessions']} sessions")
            with col5:
                st.write(f"{row['streak']}🔥 streak")
    
    with tab2:
        # Accuracy comparison
        fig1 = px.bar(
            leaderboard_df.head(10), 
            x='username', 
            y='avg_accuracy',
            title='Average Accuracy Comparison',
            color='avg_accuracy',
            color_continuous_scale='Viridis'
        )
        fig1.update_layout(xaxis_tickangle=-45)
        st.plotly_chart(fig1, use_container_width=True)
        
        # Sessions vs Accuracy scatter
        fig2 = px.scatter(
            leaderboard_df, 
            x='total_sessions', 
            y='avg_accuracy',
            size='streak',
            hover_data=['username'],
            title='Sessions vs Accuracy (Size = Streak)',
            labels={'total_sessions': 'Total Sessions', 'avg_accuracy': 'Average Accuracy (%)'}
        )
        st.plotly_chart(fig2, use_container_width=True)
    
    with tab3:
        streak_leaders = leaderboard_df.sort_values('streak', ascending=False).head(10)
        
        fig3 = px.bar(
            streak_leaders,
            x='username',
            y='streak',
            title='Streak Leaders 🔥',
            color='streak',
            color_continuous_scale='Reds'
        )
        fig3.update_layout(xaxis_tickangle=-45)
        st.plotly_chart(fig3, use_container_width=True)

# Admin Panel
def show_admin_panel():
    st.header("🛡️ Admin Analytics Dashboard")
    
    if not os.path.exists("learning_data.json"):
        st.info("No data available.")
        return
    
    with open("learning_data.json", "r") as f:
        data = json.load(f)
    
    # Overall platform stats
    total_users = len(data)
    total_sessions = sum(len(sessions) for sessions in data.values())
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("👥 Total Users", total_users)
    with col2:
        st.metric("📚 Total Sessions", total_sessions)
    with col3:
        active_users = len([u for u, s in data.items() if s and 
                          (datetime.now().date() - datetime.fromisoformat(s[-1]['timestamp']).date()).days <= 7])
        st.metric("🟢 Active Users (7d)", active_users)
    
    # Platform usage over time
    all_sessions = []
    for username, sessions in data.items():
        for session in sessions:
            session['username'] = username
            all_sessions.append(session)
    
    if all_sessions:
        df = pd.DataFrame(all_sessions)
        df['date'] = pd.to_datetime(df['date'])
        
        daily_usage = df.groupby('date').size().reset_index(name='sessions')
        
        fig = px.line(daily_usage, x='date', y='sessions', 
                     title='Platform Usage Over Time')
        st.plotly_chart(fig, use_container_width=True)
        
        # User activity breakdown
        st.subheader("📊 Detailed User Activity")
        for username, sessions in data.items():
            if sessions:
                df_user = pd.DataFrame(sessions)
                avg_acc = df_user['accuracy'].mean()
                total_sess = len(sessions)
                last_active = sessions[-1]['date']
                
                st.write(f"**{username}**: {total_sess} sessions, {avg_acc:.1f}% avg accuracy, last active: {last_active}")

# Main App Logic
init_session()

if not st.session_state.get("login", False):
    st.sidebar.title("Authentication")
    auth_choice = st.sidebar.radio("Select", ["Login", "Register"])
    if auth_choice == "Login":
        login()
    else:
        register()
else:
    st.sidebar.title("Navigation")
    show_profile()
    logout()

    if st.session_state.role == "admin":
        options = ["Upload Notes", "Ask a Question", "Interactive Quiz", "Interactive Flashcards", "Performance Analytics", "Leaderboard", "Admin Dashboard"]
    else:
        options = ["Upload Notes", "Ask a Question", "Interactive Quiz", "Interactive Flashcards", "Performance Analytics", "Leaderboard"]

    choice = st.sidebar.radio("Go to", options)

    if choice == "Upload Notes":
        upload_notes()
    elif choice == "Ask a Question":
        ask_question()
    elif choice == "Interactive Quiz":
        interactive_quiz()
    elif choice == "Interactive Flashcards":
        flashcard_learning()
    elif choice == "Performance Analytics":
        performance()
    elif choice == "Leaderboard":
        leaderboard()
    elif choice == "Admin Dashboard":
        show_admin_panel()
