import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_BASE_URL || 'http://localhost:8000';

export async function login(phone, password, fcm_token = null) {
  try {
    const device_id = "web-" + Math.random().toString(36).substring(2, 15);
    const response = await axios.post(`${API_BASE_URL}/auth/login`, {
      phone: parseInt(phone, 10),
      password,
      fcm_token,
      device_id,
    });
    return response.data;
  } catch (error) {
    if (error.response) {
      throw new Error(error.response.data.message || 'Login failed');
    } else {
      throw new Error('Network error');
    }
  }
}

export async function assignUserToProject(userId, projectId, token) {
  try {
    const response = await axios.post(
      `${API_BASE_URL}/admin/project_mapping/${userId}/${projectId}`,
      {},
      {
        headers: { Authorization: `Bearer ${token}` },
      }
    );
    return response.data;
  } catch (error) {
    if (error.response) {
      throw new Error(error.response.data.message || 'Assign user to project failed');
    } else {
      throw new Error('Network error');
    }
  }
}

export async function assignItemToProject(itemId, projectId, token) {
  try {
    const response = await axios.post(
      `${API_BASE_URL}/admin/item_mapping/${itemId}/${projectId}`,
      {},
      {
        headers: { Authorization: `Bearer ${token}` },
      }
    );
    return response.data;
  } catch (error) {
    if (error.response) {
      throw new Error(error.response.data.message || 'Assign item to project failed');
    } else {
      throw new Error('Network error');
    }
  }
}

export async function getProjectItems(projectId, token) {
  try {
    const response = await axios.get(`${API_BASE_URL}/admin/${projectId}/items`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    return response.data;
  } catch (error) {
    if (error.response) {
      throw new Error(error.response.data.message || 'Get project items failed');
    } else {
      throw new Error('Network error');
    }
  }
}

export async function getProjectUsers(projectId, token) {
  try {
    const response = await axios.get(`${API_BASE_URL}/admin/${projectId}/users`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    return response.data;
  } catch (error) {
    if (error.response) {
      throw new Error(error.response.data.message || 'Get project users failed');
    } else {
      throw new Error('Network error');
    }
  }
}

export async function getUserProjects(userId, token) {
  try {
    const response = await axios.get(`${API_BASE_URL}/admin/${userId}/projects`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    return response.data;
  } catch (error) {
    if (error.response) {
      throw new Error(error.response.data.message || 'Get user projects failed');
    } else {
      throw new Error('Network error');
    }
  }
}

export async function createProject(projectData, token) {
  try {
    const response = await axios.post(
      `${API_BASE_URL}/projects/create`,
      projectData,
      {
        headers: { Authorization: `Bearer ${token}` },
      }
    );
    return response.data;
  } catch (error) {
    if (error.response) {
      throw new Error(error.response.data.message || 'Create project failed');
    } else {
      throw new Error('Network error');
    }
  }
}

// New function to get project info including description and balance
export async function getProjectInfo(projectId, token) {
  try {
    const response = await axios.get(`${API_BASE_URL}/projects/project`, {
      headers: { Authorization: `Bearer ${token}` },
      params: { project_uuid: projectId },
    });
    return response.data;
  } catch (error) {
    if (error.response) {
      throw new Error(error.response.data.message || 'Get project info failed');
    } else {
      throw new Error('Network error');
    }
  }
}

// New function to get all users
export async function getAllUsers(token) {
  try {
    const response = await axios.get(`${API_BASE_URL}/auth/users`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    return response.data;
  } catch (error) {
    if (error.response) {
      throw new Error(error.response.data.message || 'Get all users failed');
    } else {
      throw new Error('Network error');
    }
  }
}

// New function to get all projects
export async function getAllProjects(token) {
  try {
    const response = await axios.get(`${API_BASE_URL}/projects`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    return response.data;
  } catch (error) {
    if (error.response) {
      throw new Error(error.response.data.message || 'Get all projects failed');
    } else {
      throw new Error('Network error');
    }
  }
}

// New function to get all items
export async function getAllItems(token) {
  try {
    const response = await axios.get(`${API_BASE_URL}/payments/items`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    return response.data;
  } catch (error) {
    if (error.response) {
      throw new Error(error.response.data.message || 'Get all items failed');
    } else {
      throw new Error('Network error');
    }
  }
}

// New function to create user
export async function createUser(userData, token) {
  try {
    const response = await axios.post(
      `${API_BASE_URL}/auth/register`,
      userData,
      {
        headers: { Authorization: `Bearer ${token}` },
      }
    );
    return response.data;
  } catch (error) {
    if (error.response) {
      throw new Error(error.response.data.message || 'Create user failed');
    } else {
      throw new Error('Network error');
    }
  }
}

// New function to logout user
export async function logoutUser(userId, deviceId, token) {
  try {
    const response = await axios.post(
      `${API_BASE_URL}/auth/logout`,
      {
        user_id: userId,
        device_id: deviceId,
      },
      {
        headers: { Authorization: `Bearer ${token}` },
      }
    );
    return response.data;
  } catch (error) {
    if (error.response) {
      throw new Error(error.response.data.message || 'Logout failed');
    } else {
      throw new Error('Network error');
    }
  }
}

// New function to get user details
export async function getUserDetails(userId, token) {
  try {
    const response = await axios.get(`${API_BASE_URL}/admin/user/${userId}/details`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    return response.data;
  } catch (error) {
    if (error.response) {
      throw new Error(error.response.data.message || 'Get user details failed');
    } else {
      throw new Error('Network error');
    }
  }
}
