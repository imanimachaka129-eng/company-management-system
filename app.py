# app.py
import sqlite3
from flask import Flask, g, render_template, request, redirect, url_for, flash
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'your-secret-key-change-in-production'

DATABASE = 'company.db'

def get_db():
    """Get database connection."""
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row  # Access columns by name
    return db

@app.teardown_appcontext
def close_connection(exception):
    """Close database connection at the end of request."""
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def init_db():
    """Initialize database with tables and default departments."""
    db = get_db()
    cursor = db.cursor()
    
    # Create department table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS department (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE
        )
    ''')
    
    # Create employee table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS employee (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            position TEXT,
            salary REAL,
            hire_date TEXT,
            department_id INTEGER,
            FOREIGN KEY (department_id) REFERENCES department (id) ON DELETE SET NULL
        )
    ''')
    
    # Insert default departments if they don't exist
    default_departments = ['Finance', 'Laboratory', 'Marketing', 'Employee Sector']
    for dept_name in default_departments:
        cursor.execute('INSERT OR IGNORE INTO department (name) VALUES (?)', (dept_name,))
    
    # Insert sample employees for demonstration (if table is empty)
    cursor.execute('SELECT COUNT(*) as count FROM employee')
    if cursor.fetchone()['count'] == 0:
        # Get department IDs
        cursor.execute('SELECT id, name FROM department')
        depts = {row['name']: row['id'] for row in cursor.fetchall()}
        
        sample_employees = [
            ('Alice Johnson', 'alice@company.com', 'Finance Manager', 75000, '2023-01-15', depts.get('Finance')),
            ('Bob Smith', 'bob@company.com', 'Lab Technician', 52000, '2023-03-10', depts.get('Laboratory')),
            ('Carol Davis', 'carol@company.com', 'Marketing Lead', 68000, '2022-11-20', depts.get('Marketing')),
            ('David Wilson', 'david@company.com', 'HR Specialist', 55000, '2023-06-01', depts.get('Employee Sector')),
            ('Emma Brown', 'emma@company.com', 'Financial Analyst', 62000, '2024-01-10', depts.get('Finance')),
            ('Frank Miller', 'frank@company.com', 'Research Scientist', 71000, '2023-09-05', depts.get('Laboratory'))
        ]
        for emp in sample_employees:
            cursor.execute('''
                INSERT OR IGNORE INTO employee (name, email, position, salary, hire_date, department_id)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', emp)
    
    db.commit()

@app.before_request
def before_request():
    """Initialize database before first request."""
    init_db()

# ---------- Employee Routes ----------
@app.route('/')
def index():
    """Home page - show employees with department filter."""
    department_id = request.args.get('department_id', type=int)
    db = get_db()
    cursor = db.cursor()
    
    # Fetch all departments for filter dropdown
    cursor.execute('SELECT id, name FROM department ORDER BY name')
    departments = cursor.fetchall()
    
    # Fetch employees (filtered by department if selected)
    if department_id:
        cursor.execute('''
            SELECT e.id, e.name, e.email, e.position, e.salary, e.hire_date,
                   d.name as department_name, e.department_id
            FROM employee e
            LEFT JOIN department d ON e.department_id = d.id
            WHERE e.department_id = ?
            ORDER BY e.name
        ''', (department_id,))
    else:
        cursor.execute('''
            SELECT e.id, e.name, e.email, e.position, e.salary, e.hire_date,
                   d.name as department_name, e.department_id
            FROM employee e
            LEFT JOIN department d ON e.department_id = d.id
            ORDER BY e.name
        ''')
    employees = cursor.fetchall()
    
    return render_template('index.html', employees=employees, departments=departments, selected_dept=department_id)

@app.route('/employee/add', methods=['GET', 'POST'])
def add_employee():
    """Add a new employee."""
    db = get_db()
    cursor = db.cursor()
    cursor.execute('SELECT id, name FROM department ORDER BY name')
    departments = cursor.fetchall()
    
    if request.method == 'POST':
        name = request.form['name'].strip()
        email = request.form['email'].strip()
        position = request.form['position'].strip()
        salary = request.form.get('salary', type=float)
        hire_date = request.form['hire_date']
        department_id = request.form.get('department_id', type=int)
        
        # Validation
        if not name or not email:
            flash('Name and email are required!', 'error')
            return render_template('employee_form.html', departments=departments, employee=None)
        
        try:
            cursor.execute('''
                INSERT INTO employee (name, email, position, salary, hire_date, department_id)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (name, email, position, salary, hire_date, department_id))
            db.commit()
            flash('Employee added successfully!', 'success')
            return redirect(url_for('index'))
        except sqlite3.IntegrityError:
            flash('Email already exists!', 'error')
            return render_template('employee_form.html', departments=departments, employee=None)
    
    return render_template('employee_form.html', departments=departments, employee=None)

@app.route('/employee/edit/<int:id>', methods=['GET', 'POST'])
def edit_employee(id):
    """Edit an existing employee."""
    db = get_db()
    cursor = db.cursor()
    
    if request.method == 'POST':
        name = request.form['name'].strip()
        email = request.form['email'].strip()
        position = request.form['position'].strip()
        salary = request.form.get('salary', type=float)
        hire_date = request.form['hire_date']
        department_id = request.form.get('department_id', type=int)
        
        if not name or not email:
            flash('Name and email are required!', 'error')
            cursor.execute('SELECT id, name FROM department ORDER BY name')
            departments = cursor.fetchall()
            cursor.execute('SELECT * FROM employee WHERE id = ?', (id,))
            employee = cursor.fetchone()
            return render_template('employee_form.html', departments=departments, employee=employee)
        
        try:
            cursor.execute('''
                UPDATE employee
                SET name = ?, email = ?, position = ?, salary = ?, hire_date = ?, department_id = ?
                WHERE id = ?
            ''', (name, email, position, salary, hire_date, department_id, id))
            db.commit()
            flash('Employee updated successfully!', 'success')
            return redirect(url_for('index'))
        except sqlite3.IntegrityError:
            flash('Email already exists!', 'error')
    
    # GET request - load employee data
    cursor.execute('SELECT * FROM employee WHERE id = ?', (id,))
    employee = cursor.fetchone()
    if not employee:
        flash('Employee not found!', 'error')
        return redirect(url_for('index'))
    
    cursor.execute('SELECT id, name FROM department ORDER BY name')
    departments = cursor.fetchall()
    return render_template('employee_form.html', departments=departments, employee=employee)

@app.route('/employee/delete/<int:id>', methods=['POST'])
def delete_employee(id):
    """Delete an employee."""
    db = get_db()
    cursor = db.cursor()
    cursor.execute('DELETE FROM employee WHERE id = ?', (id,))
    db.commit()
    flash('Employee deleted successfully!', 'success')
    return redirect(url_for('index'))

# ---------- Department Routes ----------
@app.route('/departments')
def list_departments():
    """List all departments with employee counts."""
    db = get_db()
    cursor = db.cursor()
    cursor.execute('''
        SELECT d.id, d.name, COUNT(e.id) as employee_count
        FROM department d
        LEFT JOIN employee e ON d.id = e.department_id
        GROUP BY d.id
        ORDER BY d.name
    ''')
    departments = cursor.fetchall()
    return render_template('departments.html', departments=departments)

@app.route('/department/add', methods=['GET', 'POST'])
def add_department():
    """Add a new department."""
    if request.method == 'POST':
        name = request.form['name'].strip()
        if not name:
            flash('Department name is required!', 'error')
            return render_template('department_form.html', department=None)
        
        db = get_db()
        cursor = db.cursor()
        try:
            cursor.execute('INSERT INTO department (name) VALUES (?)', (name,))
            db.commit()
            flash('Department added successfully!', 'success')
            return redirect(url_for('list_departments'))
        except sqlite3.IntegrityError:
            flash('Department name already exists!', 'error')
    
    return render_template('department_form.html', department=None)

@app.route('/department/edit/<int:id>', methods=['GET', 'POST'])
def edit_department(id):
    """Edit an existing department."""
    db = get_db()
    cursor = db.cursor()
    
    if request.method == 'POST':
        name = request.form['name'].strip()
        if not name:
            flash('Department name is required!', 'error')
            cursor.execute('SELECT * FROM department WHERE id = ?', (id,))
            department = cursor.fetchone()
            return render_template('department_form.html', department=department)
        
        try:
            cursor.execute('UPDATE department SET name = ? WHERE id = ?', (name, id))
            db.commit()
            flash('Department updated successfully!', 'success')
            return redirect(url_for('list_departments'))
        except sqlite3.IntegrityError:
            flash('Department name already exists!', 'error')
    
    cursor.execute('SELECT * FROM department WHERE id = ?', (id,))
    department = cursor.fetchone()
    if not department:
        flash('Department not found!', 'error')
        return redirect(url_for('list_departments'))
    return render_template('department_form.html', department=department)

@app.route('/department/delete/<int:id>', methods=['POST'])
def delete_department(id):
    """Delete a department (only if no employees are assigned)."""
    db = get_db()
    cursor = db.cursor()
    
    # Check if department has employees
    cursor.execute('SELECT COUNT(*) as count FROM employee WHERE department_id = ?', (id,))
    if cursor.fetchone()['count'] > 0:
        flash('Cannot delete department with assigned employees! Reassign or delete employees first.', 'error')
        return redirect(url_for('list_departments'))
    
    cursor.execute('DELETE FROM department WHERE id = ?', (id,))
    db.commit()
    flash('Department deleted successfully!', 'success')
    return redirect(url_for('list_departments'))

if __name__ == '__main__':
    app.run(debug=True)