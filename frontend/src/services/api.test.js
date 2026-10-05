import { beforeEach, describe, expect, it, vi } from "vitest";

const http = vi.hoisted(() => ({
  get: vi.fn(),
  post: vi.fn(),
  patch: vi.fn(),
  delete: vi.fn(),
}));

vi.mock("axios", () => ({
  default: { create: () => http },
}));

import {
  cancelReservation,
  createReservation,
  getReservation,
  updateReservation,
} from "./api";

describe("reservation API client", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("creates a reservation through the existing API contract", async () => {
    const payload = { customer_name: "Ana Pérez", guests: 2 };
    http.post.mockResolvedValue({ data: { reservation_id: "RES-123" } });

    await expect(createReservation(payload)).resolves.toEqual({ reservation_id: "RES-123" });
    expect(http.post).toHaveBeenCalledWith("/reservations/", payload);
  });

  it("uses protected contact headers for read, update and cancellation", async () => {
    const contact = { email: "ana@example.com", phone: "+34612345678" };
    const headers = {
      "X-Reservation-Email": contact.email,
      "X-Reservation-Phone": contact.phone,
    };
    const reservation = { reservation_id: "RES-123" };
    http.get.mockResolvedValue({ data: reservation });
    http.patch.mockResolvedValue({ data: reservation });
    http.delete.mockResolvedValue({});

    await expect(getReservation("RES/123", contact)).resolves.toBe(reservation);
    expect(http.get).toHaveBeenCalledWith("/reservations/RES%2F123", { headers });

    const update = { guests: 4 };
    await expect(updateReservation("RES-123", update, contact)).resolves.toBe(reservation);
    expect(http.patch).toHaveBeenCalledWith("/reservations/RES-123", update, { headers });

    await cancelReservation("RES-123", contact);
    expect(http.delete).toHaveBeenCalledWith("/reservations/RES-123", { headers });
  });
});
