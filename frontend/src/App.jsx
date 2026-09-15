// src/App.jsx
import React, { useEffect, useState } from 'react';
import {
  ThemeProvider, CssBaseline, AppBar, Toolbar, Typography, Container,
  Grid, Card, CardContent, Chip, Box, Button, CircularProgress
} from '@mui/material';
import RestaurantMenuIcon from '@mui/icons-material/RestaurantMenu';
import { theme } from './theme/theme';
import { getMenu } from './services/api';
import ChatWidget from './components/ChatWidget';

export default function App() {
  const [menu, setMenu] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getMenu()
      .then(data => setMenu(data))
      .catch(err => console.error("Error cargando menú:", err))
      .finally(() => setLoading(false));
  }, []);

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      
      {/* Navbar */}
      <AppBar position="static">
        <Toolbar>
          <RestaurantMenuIcon sx={{ mr: 2, color: 'secondary.main' }} />
          <Typography variant="h6" component="div" sx={{ flexGrow: 1, color: 'white' }}>
            Restaurante Gourmet
          </Typography>
        </Toolbar>
      </AppBar>

      {/* Hero Section */}
      <Box sx={{ bgcolor: 'primary.main', color: 'white', py: 8, textAlign: 'center' }}>
        <Container maxWidth="md">
          <Typography variant="h2" gutterBottom sx={{ color: 'secondary.main' }}>
            Sabores Inolvidables
          </Typography>
          <Typography variant="h6" paragraph sx={{ opacity: 0.9 }}>
            Cocina mediterránea tradicional con toques de vanguardia.
          </Typography>
        </Container>
      </Box>

      {/* Menú de Platos */}
      <Container sx={{ py: 6 }} maxWidth="lg">
        <Typography variant="h4" component="h2" gutterBottom align="center" sx={{ mb: 4 }}>
          Nuestra Carta
        </Typography>

        {loading ? (
          <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
            <CircularProgress color="secondary" />
          </Box>
        ) : (
          <Grid container spacing={4}>
            {menu.map((dish) => (
              <Grid item key={dish.id} xs={12} sm={6} md={4}>
                <Card sx={{ height: '100%', display: 'flex', flexDirection: 'column', borderRadius: 2 }}>
                  <CardContent sx={{ flexGrow: 1 }}>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', mb: 1 }}>
                      <Typography variant="h6" component="h3">
                        {dish.name}
                      </Typography>
                      <Typography variant="subtitle1" color="secondary.main" sx={{ fontWeight: 'bold' }}>
                        {dish.price.toFixed(2)}€
                      </Typography>
                    </Box>
                    <Typography variant="body2" color="text.secondary" paragraph>
                      {dish.description}
                    </Typography>
                    <Box sx={{ display: 'flex', gap: 0.5, flexWrap: 'wrap' }}>
                      {dish.is_vegan && <Chip label="Vegano" size="small" color="success" variant="outlined" />}
                      {dish.is_vegetarian && <Chip label="Vegetariano" size="small" color="success" variant="outlined" />}
                      {dish.allergens.map((a) => (
                        <Chip key={a} label={a} size="small" color="warning" variant="outlined" />
                      ))}
                    </Box>
                  </CardContent>
                </Card>
              </Grid>
            ))}
          </Grid>
        )}
      </Container>

      {/* Widget de Chat RAG */}
      <ChatWidget />
    </ThemeProvider>
  );
}