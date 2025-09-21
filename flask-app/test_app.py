import pytest
import json
from app import app

@pytest.fixture
def client():
    """Create test client"""
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_home_endpoint(client):
    """Test home endpoint"""
    response = client.get('/')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert 'message' in data
    assert 'Flask App Running on EKS!' in data['message']
    assert 'version' in data
    assert 'timestamp' in data

def test_health_endpoint(client):
    """Test health check endpoint"""
    response = client.get('/health')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['status'] == 'healthy'
    assert 'timestamp' in data

def test_ready_endpoint(client):
    """Test readiness check endpoint"""
    response = client.get('/ready')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['status'] == 'ready'

def test_get_tasks(client):
    """Test get all tasks"""
    response = client.get('/tasks')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert 'tasks' in data
    assert 'count' in data
    assert isinstance(data['tasks'], list)

def test_get_single_task(client):
    """Test get single task"""
    response = client.get('/tasks/1')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['id'] == 1
    assert 'title' in data

def test_get_nonexistent_task(client):
    """Test get non-existent task"""
    response = client.get('/tasks/999')
    assert response.status_code == 404
    data = json.loads(response.data)
    assert data['error'] == 'Task not found'

def test_create_task(client):
    """Test create new task"""
    new_task = {
        'title': 'Test Task',
        'description': 'This is a test task'
    }
    response = client.post('/tasks',
                          data=json.dumps(new_task),
                          content_type='application/json')
    assert response.status_code == 201
    data = json.loads(response.data)
    assert data['title'] == new_task['title']
    assert data['description'] == new_task['description']
    assert data['completed'] == False
    assert 'id' in data

def test_create_task_missing_title(client):
    """Test create task without title"""
    new_task = {
        'description': 'This task has no title'
    }
    response = client.post('/tasks',
                          data=json.dumps(new_task),
                          content_type='application/json')
    assert response.status_code == 400
    data = json.loads(response.data)
    assert data['error'] == 'Title is required'

def test_update_task(client):
    """Test update existing task"""
    update_data = {
        'title': 'Updated Task',
        'completed': True
    }
    response = client.put('/tasks/1',
                         data=json.dumps(update_data),
                         content_type='application/json')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['title'] == update_data['title']
    assert data['completed'] == update_data['completed']

def test_update_nonexistent_task(client):
    """Test update non-existent task"""
    update_data = {
        'title': 'Updated Task'
    }
    response = client.put('/tasks/999',
                         data=json.dumps(update_data),
                         content_type='application/json')
    assert response.status_code == 404
    data = json.loads(response.data)
    assert data['error'] == 'Task not found'

def test_delete_task(client):
    """Test delete task"""
    response = client.delete('/tasks/2')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert 'message' in data
    assert 'deleted successfully' in data['message']

def test_delete_nonexistent_task(client):
    """Test delete non-existent task"""
    response = client.delete('/tasks/999')
    assert response.status_code == 404
    data = json.loads(response.data)
    assert data['error'] == 'Task not found'

def test_metrics_endpoint(client):
    """Test metrics endpoint"""
    response = client.get('/metrics')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert 'total_tasks' in data
    assert 'completed_tasks' in data
    assert 'pending_tasks' in data
    assert 'timestamp' in data
    assert isinstance(data['total_tasks'], int)

def test_404_endpoint(client):
    """Test 404 error handling"""
    response = client.get('/nonexistent')
    assert response.status_code == 404
    data = json.loads(response.data)
    assert data['error'] == 'Endpoint not found'