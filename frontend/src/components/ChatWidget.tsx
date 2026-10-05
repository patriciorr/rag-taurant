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
  const [sessionId] = useState(() => crypto.randomUUID());
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
      const data = await sendChatMessage(userText, sessionId);
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
    <Box sx={{ position: 'fixed', bottom: 16, right: 16, zIndex: 1000 }}>
      {!open && (
        <Fab
          onClick={() => setOpen(true)}
          aria-label="Abrir el chat"
          sx={{
            bgcolor: "var(--gold-light)",
            color: "var(--green)",
            "&:hover": { bgcolor: "#d8ad78" },
          }}
        >
          <SmartToyIcon />
        </Fab>
      )}

      <Slide direction="up" in={open} mountOnEnter unmountOnExit>
        <Paper elevation={8} sx={{ width: { xs: 'calc(100vw - 32px)', sm: 360 }, maxWidth: 'calc(100vw - 32px)', height: { xs: 'min(500px, calc(100dvh - 100px))', sm: 500 }, display: 'flex', flexDirection: 'column', borderRadius: 3, overflow: 'hidden', fontFamily: 'var(--sans)', '& .MuiTypography-root, & .MuiInputBase-root': { fontFamily: 'var(--sans)' }, '& .MuiInputBase-root': { fontSize: '1rem' } }}>
          {/* Header */}
          <Box sx={{ p: 2, bgcolor: 'var(--green)', color: 'white', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <Typography variant="h6" sx={{ fontSize: '1.1rem', fontFamily: 'var(--serif) !important' }}>Asistente Gourmet</Typography>
            <IconButton size="small" onClick={() => setOpen(false)} sx={{ color: 'white' }} aria-label="Cerrar el chat">
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
                      bgcolor: msg.sender === 'user' ? 'var(--gold)' : 'white',
                      color: msg.sender === 'user' ? 'var(--green)' : 'text.primary',
                    }}
                  >
                    <ListItemText primary={msg.text} primaryTypographyProps={{ variant: 'body1' }} />
                  </Paper>
                </ListItem>
              ))}
              {loading && (
                <Box sx={{ display: 'flex', justifyContent: 'center', my: 1 }}>
                  <CircularProgress size={24} sx={{ color: 'var(--gold)' }} />
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
            <IconButton
              onClick={handleSend}
              disabled={loading}
              sx={{ color: 'var(--gold-light)', '&:hover': { color: '#d8ad78' } }}
            >
              <SendIcon />
            </IconButton>
          </Box>
        </Paper>
      </Slide>
    </Box>
  );
}