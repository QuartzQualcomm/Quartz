// import { BrowserWindow } from "electron";
import axios from "axios";

// Extract the base URL into a constant for easier configuration
const API_BASE_URL = "http://192.168.46.138:8000";

export const ipcQuartz = {
  handleLLMResponse: async (_: any, command: string, context: any) => {
    try {
      console.log("Handling LLM response with command:", command);
      const response = await axios.post(`${API_BASE_URL}/api/llm`, {
        command,
        context
      });
      return response.data;
    } catch (error) {
      console.error("Error handling LLM response:", error);
      throw error;
    }
  },
  transcribeAudio: async (_: any, audioData: any) => {
    try {
      console.log("HI HI HI HI ");
      // console.log(audioData);
      console.log("HI HI HI HIHI ")

      const response = await axios.post(`${API_BASE_URL}/api/transcribe`, {
        audioData
      });
      console.log(response);
      return response.data.data;
    } catch (error) {
      console.error("Error transcribing audio:");
      // throw error;
    }
  },
  directToolRemoveBg: async (_: any, imagePath: any) => {
    console.log("Removing background from image:", imagePath);
    try {
      const response = await axios.post(`${API_BASE_URL}/api/image/remove-bg`, {
        image_path: imagePath
      });
      console.log("Response from remove background API:", response.data);
      return response.data;
    }
    catch (error) {
      console.error("Error removing background from image:", error);
      throw error;
    }
  },
  directToolPotraitBlur: async (_: any, imagePath: any) => {
    console.log("Blurring portrait in image:", imagePath);
    try {
      const response = await axios.post(`${API_BASE_URL}/api/image/portrait-effect`, {
        image_path: imagePath
      });
      console.log("Response from portrait blur API:", response.data);
      return response.data;
    }
    catch (error) {
      console.error("Error blurring portrait in image:", error);
      throw error;
    }
  }
};
