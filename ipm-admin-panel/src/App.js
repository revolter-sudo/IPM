import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate, useParams } from 'react-router-dom';
import LoginPage from './pages/LoginPage';
import AdminDashboard from './pages/AdminDashboard';
import ProjectDetails from './components/ProjectDetails';
import UserDetails from './components/UserDetails';

// Wrapper component to extract projectId from route params and pass to ProjectDetails
function ProjectDetailsWrapper({ token }) {
  const { projectId } = useParams();
  return <ProjectDetails projectId={projectId} token={token} />;
}

// Wrapper component to extract userId from route params and pass to UserDetails
function UserDetailsWrapper({ token }) {
  const { userId } = useParams();
  return <UserDetails userId={userId} token={token} />;
}

function App() {
  // Retrieve token from localStorage
  const token = localStorage.getItem('token');

  return (
    <Router>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/admin-dashboard" element={<AdminDashboard token={token} />} />
        <Route path="/project-details/:projectId" element={<ProjectDetailsWrapper token={token} />} />
        <Route path="/user-details/:userId" element={<UserDetailsWrapper token={token} />} />
        <Route path="*" element={<Navigate to="/login" replace />} />
      </Routes>
    </Router>
  );
}

export default App;
