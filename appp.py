
import streamlit as st
import sqlite3
import pandas as pd

# ---------------- DATABASE CONNECTION ----------------

conn = sqlite3.connect("students.db", check_same_thread=False)

conn.execute("""
CREATE TABLE IF NOT EXISTS students (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    roll TEXT UNIQUE,
    name TEXT,
    standard TEXT,
    stream TEXT
)
""")

conn.execute("""
CREATE TABLE IF NOT EXISTS marks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER,
    subject TEXT,
    marks REAL,
    maximum REAL,
    UNIQUE(student_id, subject),
    FOREIGN KEY(student_id) REFERENCES students(id)
)
""")

conn.commit()

# ---------------- PAGE CONFIGURATION ----------------

st.set_page_config(
    page_title="Student Grade Management",
    page_icon="🎓",
    layout="wide"
)

st.title("🎓 Student Grade Management System")
st.write("Manage students, marks, results and rankings.")

# ---------------- SIDEBAR ----------------

menu = st.sidebar.selectbox(
    "Navigation",
    [
        "Dashboard",
        "Add Student",
        "View Students",
        "Enter Marks",
        "Results & Rankings",
        "Delete Student"
    ]
)

# ---------------- DASHBOARD ----------------

if menu == "Dashboard":

    st.header("Dashboard")

    students = pd.read_sql_query(
        "SELECT * FROM students", conn
    )

    marks = pd.read_sql_query(
        "SELECT * FROM marks", conn
    )

    c1, c2, c3 = st.columns(3)

    c1.metric("Total Students", len(students))
    c2.metric("Marks Entries", len(marks))

    c3.metric(
        "Students with Marks",
        marks["student_id"].nunique() if not marks.empty else 0
    )

    st.subheader("Welcome!")
    st.write("Use the sidebar to manage student records.")

# ---------------- ADD STUDENT ----------------

elif menu == "Add Student":

    st.header("Add New Student")

    with st.form("student_form"):

        roll = st.text_input("Roll Number")
        name = st.text_input("Student Name")
        standard = st.text_input("Class")
        stream = st.selectbox(
            "Stream",
            ["Science", "Commerce", "Arts", "Other"]
        )

        submit = st.form_submit_button("Add Student")

        if submit:

            if roll and name and standard:

                try:
                    conn.execute("""
                        INSERT INTO students
                        (roll, name, standard, stream)
                        VALUES (?, ?, ?, ?)
                    """, (roll, name, standard, stream))

                    conn.commit()
                    st.success("Student added successfully!")

                except sqlite3.IntegrityError:
                    st.error("Roll number already exists.")

            else:
                st.warning("Please fill all fields.")

# ---------------- VIEW STUDENTS ----------------

elif menu == "View Students":

    st.header("Student Records")

    df = pd.read_sql_query("""
        SELECT roll AS Roll,
               name AS Name,
               standard AS Class,
               stream AS Stream
        FROM students
        ORDER BY roll
    """, conn)

    st.dataframe(df, use_container_width=True)

    st.download_button(
        "Download Student List",
        df.to_csv(index=False),
        "students.csv",
        "text/csv"
    )

# ---------------- ENTER MARKS ----------------

elif menu == "Enter Marks":

    st.header("Enter Student Marks")

    students = pd.read_sql_query(
        "SELECT * FROM students ORDER BY roll", conn
    )

    if students.empty:

        st.warning("Please add students first.")

    else:

        student_options = {
            f"{row['roll']} - {row['name']}": row["id"]
            for _, row in students.iterrows()
        }

        with st.form("marks_form"):

            selected = st.selectbox(
                "Select Student",
                list(student_options.keys())
            )

            subject = st.text_input("Subject")

            col1, col2 = st.columns(2)

            marks = col1.number_input(
                "Marks Obtained",
                min_value=0.0,
                value=0.0
            )

            maximum = col2.number_input(
                "Maximum Marks",
                min_value=1.0,
                value=100.0
            )

            submit = st.form_submit_button("Save Marks")

            if submit:

                if not subject.strip():
                    st.error("Enter a subject name.")

                elif marks > maximum:
                    st.error("Marks cannot exceed maximum marks.")

                else:

                    try:
                        conn.execute("""
                            INSERT INTO marks
                            (student_id, subject, marks, maximum)
                            VALUES (?, ?, ?, ?)
                        """, (
                            student_options[selected],
                            subject.strip(),
                            marks,
                            maximum
                        ))

                        conn.commit()
                        st.success("Marks saved successfully!")

                    except sqlite3.IntegrityError:
                        st.error(
                            "Marks for this subject already exist."
                        )

# ---------------- RESULTS AND RANKINGS ----------------

elif menu == "Results & Rankings":

    st.header("Student Results & Rankings")

    df = pd.read_sql_query("""
        SELECT
            s.roll AS Roll,
            s.name AS Name,
            s.standard AS Class,
            s.stream AS Stream,
            SUM(m.marks) AS Total,
            SUM(m.maximum) AS Maximum,
            COUNT(m.id) AS Subjects,
            MIN(m.marks * 100.0 / m.maximum) AS Lowest_Subject_Percentage
        FROM students s
        JOIN marks m ON s.id = m.student_id
        GROUP BY s.id
    """, conn)

    if df.empty:

        st.info("No marks available yet.")

    else:

        df["Percentage"] = (
            df["Total"] / df["Maximum"] * 100
        ).round(2)

        df["Result"] = df["Lowest_Subject_Percentage"].apply(
            lambda x: "PASS" if x >= 40 else "FAIL"
        )

        df = df.sort_values(
            "Percentage",
            ascending=False
        ).reset_index(drop=True)

        df.insert(0, "Rank", range(1, len(df) + 1))

        st.dataframe(
            df.drop(columns=["Lowest_Subject_Percentage"]),
            use_container_width=True
        )

        st.subheader("Performance Chart")

        st.bar_chart(
            df.set_index("Name")["Percentage"]
        )

        st.download_button(
            "Download Results",
            df.to_csv(index=False),
            "student_results.csv",
            "text/csv"
        )

# ---------------- DELETE STUDENT ----------------

elif menu == "Delete Student":

    st.header("Delete Student")

    students = pd.read_sql_query(
        "SELECT * FROM students ORDER BY roll", conn
    )

    if students.empty:

        st.info("No students available.")

    else:

        options = {
            f"{row['roll']} - {row['name']}": row["id"]
            for _, row in students.iterrows()
        }

        selected = st.selectbox(
            "Select Student",
            list(options.keys())
        )

        confirm = st.checkbox(
            "I confirm that I want to delete this student and their marks."
        )

        if st.button("Delete Student", disabled=not confirm):

            student_id = options[selected]

            conn.execute(
                "DELETE FROM marks WHERE student_id = ?",
                (student_id,)
            )

            conn.execute(
                "DELETE FROM students WHERE id = ?",
                (student_id,)
            )

            conn.commit()

            st.success("Student deleted successfully!")
            st.rerun()

# ---------------- FOOTER ----------------

st.sidebar.divider()
st.sidebar.caption("Student Grade Management System")
st.sidebar.caption("Developed using Python and Streamlit")
