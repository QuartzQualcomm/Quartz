import { createStore } from "zustand/vanilla";

export interface IChatLLMPanelStore {
  list: any[];
  isLoad: boolean;

  addList: (element: any) => void;
}

export const chatLLMStore = createStore<IChatLLMPanelStore>((set) => ({
  list: [],
  isLoad: false,

  addList: (element: any) => set((state) => ({ list: [...state.list, element] })),
}));
