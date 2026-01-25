import { randomUUID } from "crypto";

export interface IStorage {
  // Minimal storage interface - actual data is managed by Python backend
}

export class MemStorage implements IStorage {
  constructor() {}
}

export const storage = new MemStorage();
