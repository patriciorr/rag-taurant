import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import ChatWidget from './ChatWidget';
import { sendChatMessage } from '../services/api';

vi.mock('../services/api', () => ({ sendChatMessage: vi.fn() }));

describe('ChatWidget message formatting', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    Element.prototype.scrollIntoView = vi.fn();
  });

  async function send(user, text) {
    await user.click(screen.getByRole('button', { name: 'Abrir el chat' }));
    await user.type(screen.getByPlaceholderText('Escribe tu consulta...'), `${text}{Enter}`);
  }

  it('renders assistant emphasis, lists and paragraphs while keeping user text literal', async () => {
    const user = userEvent.setup();
    sendChatMessage.mockResolvedValue({
      response: 'Te recomiendo:\n\n- **Gazpacho** (8,50 €)\n- *Espinacas*\n\n¿Quieres reservar?',
    });
    render(<ChatWidget />);
    await send(user, '¿Qué significa **vegano**?');

    expect(await screen.findByText('Gazpacho')).toHaveProperty('tagName', 'STRONG');
    const list = screen.getByText('Gazpacho').closest('ul');
    expect(within(list).getAllByRole('listitem')).toHaveLength(2);
    expect(screen.getByText('Espinacas').tagName).toBe('EM');
    expect(screen.getByText('¿Quieres reservar?').tagName).toBe('P');
    expect(screen.getByText('¿Qué significa **vegano**?')).toBeInTheDocument();
  });

  it('renders numbered reservation details and keeps the confirmation outside the list', async () => {
    const user = userEvent.setup();
    sendChatMessage.mockResolvedValue({
      response:
        'Revisa los datos:\n\n1. Nombre: Ana \\*\\*Pérez\\*\\* \\<Ana\\>\n2. Comensales: 2\n\nTodavía no se ha creado. Responde «sí».',
    });
    render(<ChatWidget />);
    await send(user, 'Quiero reservar');

    const confirmation = await screen.findByText(/Todavía no se ha creado/);
    const list = document.querySelector('ol');
    expect(within(list).getAllByRole('listitem')).toHaveLength(2);
    expect(within(list).getByText('Nombre: Ana **Pérez** <Ana>')).toBeInTheDocument();
    expect(list).not.toContainElement(confirmation);
  });

  it('does not render HTML, links, or images from assistant responses', async () => {
    const user = userEvent.setup();
    sendChatMessage.mockResolvedValue({
      response:
        '<img src=x onerror="alert(1)">\n\n[Enlace](https://example.com) ![Imagen](https://example.com/image.png)',
    });
    render(<ChatWidget />);
    await send(user, 'Hola');

    expect(await screen.findByText(/Enlace/)).toBeInTheDocument();
    expect(screen.queryByRole('link', { name: 'Enlace' })).not.toBeInTheDocument();
    expect(document.querySelector('img[src*="example.com"], img[src="x"]')).toBeNull();
  });
});
