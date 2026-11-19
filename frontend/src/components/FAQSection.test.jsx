import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import FAQSection from './FAQSection';

describe('FAQSection', () => {
  it('explains how to use the demo and how submitted data is handled', () => {
    render(<FAQSection />);

    expect(
      screen.getByRole('heading', { name: 'Preguntas frecuentes' }),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/nombre, correo electrónico, teléfono, fecha, hora/),
    ).toBeInTheDocument();
    expect(screen.getByText(/Google Gemini/)).toBeInTheDocument();
    expect(screen.getByText(/MongoDB/)).toBeInTheDocument();
    expect(
      screen.getByText(/proyecto personal de portfolio/),
    ).toBeInTheDocument();
  });
});
