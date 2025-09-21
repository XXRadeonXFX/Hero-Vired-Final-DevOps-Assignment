from flask import Flask, jsonify, request
import os
import json
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Configuration
app.config['DEBUG'] = os.getenv('FLASK_DEBUG', 'False').lower() in ['true', '1', 't']
app.config['HOST'] = os.getenv('FLASK_HOST', '0.0.0.0')
app.config['PORT'] = int(os.getenv('FLASK_PORT', 5000))

# In-memory storage for demo purposes
tasks = [
    {
        "id": 1,
        "title": "Learn Docker",
        "description": "Understand containerization",
        "completed": False,
        "created_at": "2024-01-01T00:00:00Z"
    },
    {
        "id": 2,
        "title": "Learn Kubernetes",
        "description": "Master container orchestration",
        "completed": False,
        "created_at": "2024-01-02T00:00:00Z"
    }
]

@app.route('/')
def home():
    """Home endpoint"""
    return jsonify({
        "message": "Flask App Running on EKS!",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "environment": os.getenv('ENVIRONMENT', 'development'),
        "kubernetes_info": {
            "pod_name": os.getenv('HOSTNAME', 'unknown'),
            "namespace": os.getenv('POD_NAMESPACE', 'default'),
            "node_name": os.getenv('NODE_NAME', 'unknown')
        }
    })

@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "uptime": "Service is running"
    }), 200

@app.route('/ready')
def ready():
    """Readiness check endpoint"""
    return jsonify({
        "status": "ready",
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }), 200

@app.route('/tasks', methods=['GET'])
def get_tasks():
    """Get all tasks"""
    logger.info("Fetching all tasks")
    return jsonify({
        "tasks": tasks,
        "count": len(tasks)
    })

@app.route('/tasks/<int:task_id>', methods=['GET'])
def get_task(task_id):
    """Get a specific task"""
    logger.info(f"Fetching task with ID: {task_id}")
    task = next((task for task in tasks if task["id"] == task_id), None)
    if task:
        return jsonify(task)
    else:
        return jsonify({"error": "Task not found"}), 404

@app.route('/tasks', methods=['POST'])
def create_task():
    """Create a new task"""
    try:
        data = request.get_json()
        if not data or 'title' not in data:
            return jsonify({"error": "Title is required"}), 400
        
        new_task = {
            "id": max([task["id"] for task in tasks], default=0) + 1,
            "title": data["title"],
            "description": data.get("description", ""),
            "completed": False,
            "created_at": datetime.utcnow().isoformat() + "Z"
        }
        
        tasks.append(new_task)
        logger.info(f"Created new task: {new_task['id']}")
        return jsonify(new_task), 201
    
    except Exception as e:
        logger.error(f"Error creating task: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@app.route('/tasks/<int:task_id>', methods=['PUT'])
def update_task(task_id):
    """Update a task"""
    try:
        task = next((task for task in tasks if task["id"] == task_id), None)
        if not task:
            return jsonify({"error": "Task not found"}), 404
        
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400
        
        task["title"] = data.get("title", task["title"])
        task["description"] = data.get("description", task["description"])
        task["completed"] = data.get("completed", task["completed"])
        
        logger.info(f"Updated task: {task_id}")
        return jsonify(task)
    
    except Exception as e:
        logger.error(f"Error updating task {task_id}: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@app.route('/tasks/<int:task_id>', methods=['DELETE'])
def delete_task(task_id):
    """Delete a task"""
    try:
        global tasks
        task = next((task for task in tasks if task["id"] == task_id), None)
        if not task:
            return jsonify({"error": "Task not found"}), 404
        
        tasks = [task for task in tasks if task["id"] != task_id]
        logger.info(f"Deleted task: {task_id}")
        return jsonify({"message": f"Task {task_id} deleted successfully"})
    
    except Exception as e:
        logger.error(f"Error deleting task {task_id}: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@app.route('/metrics')
def metrics():
    """Basic metrics endpoint"""
    return jsonify({
        "total_tasks": len(tasks),
        "completed_tasks": len([task for task in tasks if task["completed"]]),
        "pending_tasks": len([task for task in tasks if not task["completed"]]),
        "timestamp": datetime.utcnow().isoformat() + "Z"
    })

@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Endpoint not found"}), 404

@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Internal server error: {str(error)}")
    return jsonify({"error": "Internal server error"}), 500

if __name__ == '__main__':
    logger.info(f"Starting Flask app on {app.config['HOST']}:{app.config['PORT']}")
    logger.info(f"Debug mode: {app.config['DEBUG']}")
    app.run(
        host=app.config['HOST'],
        port=app.config['PORT'],
        debug=app.config['DEBUG']
    )