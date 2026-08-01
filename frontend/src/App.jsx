import React from "react";
import { Routes, Route } from "react-router-dom";
import Navbar from "./components/Navbar.jsx";
import Home from "./pages/Home.jsx";
import Login from "./pages/Login.jsx";
import Register from "./pages/Register.jsx";
import BookDetail from "./pages/BookDetail.jsx";
import ForYou from "./pages/ForYou.jsx";

export default function App() {
  return (
    <div className="min-h-screen bg-paper text-ink">
      <Navbar />
      <main className="max-w-5xl mx-auto px-6 py-8">
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />
          <Route path="/books/:bookId" element={<BookDetail />} />
          <Route path="/for-you" element={<ForYou />} />
        </Routes>
      </main>
    </div>
  );
}
