import { createStore } from "zustand/vanilla";

export interface IChatLLMPanelStore {
  list: any[];
  isLoad: boolean;

  addList: (element: any) => void;
}

export const chatLLMStore = createStore<IChatLLMPanelStore>((set) => ({
  list: [
    {
      from: "agent",
      text: "Hello, I'm Quartz! I'm your personal local AI video editor powered by Qualcomm Snapdragon X. Start by giving me commands!",
      timestamp: new Date().toISOString(),
    }
  ],
  isLoad: false,

  addList: (element: any) => set((state) => ({ list: [...state.list, element] })),
}));
