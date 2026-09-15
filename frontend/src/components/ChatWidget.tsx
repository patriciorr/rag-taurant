// src/components/ChatWidget.jsx
import React, { useState, useRef, useEffect } from 'react';
import {
  Box, Fab, Paper, Typography, TextField, IconButton,
  List, ListItem, ListItemText, CircularProgress, Slide
} from '@mui/material';
import SmartToyIcon from '@mui/icons-material/SmartToy';
import CloseIcon from '@mui/icons-material/Close';
import SendIcon from '@mui/icons-material/Send';
import { sendChatMessage } from '../services/api';

export default function ChatWidget() {
  const [open, setOpen] = useState(false);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [messages, setMessages] = useState([
    { sender: 'bot', text: '¡Hola! Soy el asistente virtual del restaurante. ¿En qué puedo ayudarte hoy?' }
  ]);
  
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    if (open) scrollToBottom();
  }, [messages, open]);

  const handleSend = async () => {
    if (!input.trim() || loading) return;

    const userText = input;
    setInput('');
    setMessages((prev) => [...prev, { sender: 'user', text: userText }]);
    setLoading(true);

    try {
      const data = await sendChatMessage(userText);
      setMessages((prev) => [...prev, { sender: 'bot', text: data.response }]);
    } catch (error) {
      setMessages((prev) => [
        ...prev,
        { sender: 'bot', text: 'Lo siento, ha ocurrido un error de conexión con el servidor.' }
      ]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Box sx={{ position: 'fixed', bottom: 24, right: 24, zIndex: 1000 }}>
      {!open && (
        <Fab color="secondary" onClick={() => setOpen(true)} aria-label="chat">
          <SmartToyIcon />
        </Fab>
      )}

      <Slide direction="up" in={open} mountOnEnter unmountOnExit>
        <Paper elevation={8} sx={{ width: 360, height: 500, display: 'flex', flexDirection: 'column', borderRadius: 3, overflow: 'hidden' }}>
          {/* Header */}
          <Box sx={{ p: 2, bgcolor: 'primary.main', color: 'white', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <Typography variant="h6" sx={{ fontSize: '1.1rem' }}>Asistente Gourmet</Typography>
            <IconButton size="small" onClick={() => setOpen(false)} sx={{ color: 'white' }}>
              <CloseIcon />
            </IconButton>
          </Box>

          {/* Lista de Mensajes */}
          <Box sx={{ flexGrow: 1, p: 2, overflowY: 'auto', bgcolor: 'background.default' }}>
            <List disablePadding>
              {messages.map((msg, idx) => (
                <ListItem key={idx} sx={{ justifyContent: msg.sender === 'user' ? 'flex-end' : 'flex-start', px: 0, py: 0.5 }}>
                  <Paper
                    elevation={1}
                    sx={{
                      p: 1.5,
                      maxWidth: '80%',
                      borderRadius: 2,
                      bgcolor: msg.sender === 'user' ? 'secondary.main' : 'white',
                      color: msg.sender === 'user' ? 'white' : 'text.primary',
                    }}
                  >
                    <ListItemText primary={msg.text} primaryTypographyProps={{ variant: 'body2' }} />
                  </Paper>
                </ListItem>
              ))}
              {loading && (
                <Box sx={{ display: 'flex', justifyContent: 'center', my: 1 }}>
                  <CircularProgress size={24} color="secondary" />
                </Box>
              )}
              <div ref={messagesEndRef} />
            </List>
          </Box>

          {/* Input de Texto */}
          <Box sx={{ p: 1.5, bgcolor: 'white', borderTop: '1px solid #eee', display: 'flex' }}>
            <TextField
              fullWidth
              size="small"
              placeholder="Escribe tu consulta..."
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && handleSend()}
            />
            <IconButton color="primary" onClick={handleSend} disabled={loading}>
              <SendIcon />
            </IconButton>
          </Box>
        </Paper>
      </Slide>
    </Box>
  );
}