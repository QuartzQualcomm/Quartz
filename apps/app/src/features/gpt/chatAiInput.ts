import { LitElement, PropertyValues, html } from "lit";
import { customElement, property } from "lit/decorators.js";
import { ITimelineStore, useTimelineStore } from "../../states/timelineStore";
import { IUIStore, uiStore } from "../../states/uiStore";
import { chatLLMStore, IChatLLMPanelStore } from "../../states/chatLLM";
import { ToastController } from "../../controllers/toast";
import { actionParsor, parseCommands } from "./resultParser";
import { getLocationEnv } from "../../functions/getLocationEnv";
import {
  addTextElement,
  addShapeElement,
  renderNewImage,
  addSlideElement,
  addElement,
  exportVideo
} from "../../../reponseHandlers";

@customElement("chat-ai-input")
export class ChatAiInput extends LitElement {
  isEnter: boolean;
  isRecording: boolean;
  mediaRecorder: MediaRecorder | null;
  audioChunks: Blob[];

  @property({ type: String })
  textContent: string = "";

  @property({ type: String })
  currentPlaceholder: string = "Ask me anything...";

  private placeholderInterval: any;
  private placeholders = [
    "Can you write 'My awesome video' on the selected clip?",
    "Add a red circle",
    "Color transfer barbie to this image",
    "Give me the portrait effect of this image",
  ];

  constructor() {
    super();
    this.isEnter = false;
    this.isRecording = false;
    this.mediaRecorder = null;
    this.audioChunks = [];
  }

  connectedCallback() {
    super.connectedCallback();
    let placeholderIndex = 0;
    this.placeholderInterval = setInterval(() => {
      placeholderIndex = (placeholderIndex + 1) % this.placeholders.length;
      this.currentPlaceholder = this.placeholders[placeholderIndex];
    }, 3000);
  }

  disconnectedCallback() {
    super.disconnectedCallback();
    clearInterval(this.placeholderInterval);
  }

  toast = new ToastController(this);

  @property()
  uiState: IUIStore = uiStore.getInitialState();
  chatLLMState: IChatLLMPanelStore = chatLLMStore.getInitialState();
  timelineState: ITimelineStore = useTimelineStore.getInitialState();

  @property({ type: Boolean })
  hideOpenButton = false; // This will effectively be true for this component

  createRenderRoot() {
    if (getLocationEnv() != "electron") {
      this.classList.add("d-none");
    }

    useTimelineStore.subscribe((state) => {
      // No direct UI change, but state is kept in sync
      this.timelineState = state; 
    });

    uiStore.subscribe((state) => {
      this.uiState = state;
      this.requestUpdate();
    });

    chatLLMStore.subscribe((state) => {
      this.chatLLMState = state;
      this.requestUpdate();
    });

    return this;
  }

  async toggleRecording() {
    if (this.isRecording) {
      this.stopRecording();
    } else {
      await this.startRecording();
    }
    this.requestUpdate(); // Ensure LitElement re-renders
  }

  async startRecording() {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      this.audioChunks = [];

      const options = MediaRecorder.isTypeSupported("audio/wav")
        ? { mimeType: "audio/wav" }
        : {};

      this.mediaRecorder = new MediaRecorder(stream, options);

      this.mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          this.audioChunks.push(event.data);
        }
      };

      this.mediaRecorder.onstop = () => {
        const audioBlob = new Blob(this.audioChunks, {
          type: this.mediaRecorder?.mimeType || "audio/webm",
        });
        const reader = new FileReader();
        reader.readAsDataURL(audioBlob);
        reader.onloadend = () => {
          const base64data = reader.result as string;
          window.electronAPI.req.quartz
            .transcribeAudio(base64data)
            .then((transcription) => {
              this.textContent = transcription || "";
              this.isRecording = false;
            })
            .catch((err) => {
              this.toast.show("Transcription failed", 2000);
              this.isRecording = false;
            })
            .finally(() => {
              stream.getTracks().forEach((track) => track.stop());
              this.mediaRecorder = null;
            });
        };
      };

      this.mediaRecorder.start();
      this.isRecording = true;
    } catch (err: unknown) {
      console.error("Error accessing microphone or starting recording:", err);

      this.toast.show(
        "Error accessing microphone: " +
          (err instanceof Error ? err.message : String(err)),
        3000,
      );
      this.isRecording = false; // Ensure state is correct on error
      if (this.mediaRecorder) {
        // Clean up if mediaRecorder was partially initialized
        this.mediaRecorder.stream.getTracks().forEach((track) => track.stop());
        this.mediaRecorder = null;
      }
    }
    this.requestUpdate();
  }

  stopRecording() {
    if (this.mediaRecorder && this.mediaRecorder.state !== "inactive") {
      this.mediaRecorder.stop();
      // onstop event will handle state changes and cleanup
    } else {
      // Fallback if stopRecording is called unexpectedly
      this.isRecording = false;
      this.requestUpdate();
    }
  }

  handleEnter(event) {

    const aiInput = document.querySelector("ai-input");
    return aiInput.handleEnter(event);
    
  }

  executeFunction(value) {
    console.log("Entered value:", value);
    const lists = this.mapTimeline();
    console.log("Timeline lists:", lists);

    console.log(`${lists.join(" ")} \n ${value}`);

    const directory = document.querySelector("asset-list").nowDirectory;
    if (directory == "") {
      this.toast.show("Please specify a directory", 2000);
      return 0;
    }

    window.electronAPI.req.filesystem.getDirectory(directory).then((result) => {
      let fileLists = {};
      let resultList: any = [];
      console.log(directory, result);

      for (const key in result) {
        if (Object.hasOwnProperty.call(result, key)) {
          const element = result[key];
          if (!element.isDirectory) {
            fileLists[key] = element;
          }
        }
      }

      for (const file in fileLists) {
        if (Object.hasOwnProperty.call(fileLists, file)) {
          const element = fileLists[file];
          const path = directory + "/" + element.title;
          console.log(path);
          resultList.push(`EXIST "${path}"`);
        }
      }
    });
  }

  mapTimeline(): string[] {
    const list: any = [];
    const timeline = useTimelineStore.getState();
    for (const key in timeline.timeline) {
      if (Object.prototype.hasOwnProperty.call(timeline.timeline, key)) {
        const element = timeline.timeline[key];
        if (element.filetype == "text") {
          const options = [
            `x=${element.location?.x}`,
            `y=${element.location?.y}`,
            `w=${element.width}`,
            `h=${element.height}`,
            `t=${element.startTime}`,
            `d=${element.duration}`,
          ];
          list.push(`TEXT "${element.text}" ${options.join(":")}`);
        } else if (element.filetype == "image") {
          const options = [
            `x=${element.location?.x}`,
            `y=${element.location?.y}`,
            `w=${element.width}`,
            `h=${element.height}`,
            `t=${element.startTime}`,
            `d=${element.duration}`,
          ];
          list.push(`IMAGE "${key}" ${options.join(":")}`);
        } else if (element.filetype == "video") {
          const options = [
            `x=${element.location?.x}`,
            `y=${element.location?.y}`,
            `w=${element.width}`,
            `h=${element.height}`,
            `t=${element.startTime}`,
            `d=${element.duration}`,
          ];
          list.push(`VIDEO "${key}" ${options.join(":")}`);
        } else if (element.filetype == "audio") {
          const options = [`t=${element.startTime}`, `d=${element.duration}`];
          list.push(`AUDIO "${key}" ${options.join(":")}`);
        }
      }
    }

    return list;
  }

  handleClickInput() {
    this.timelineState.setCursorType("lockKeyboard");
  }

  panelOpen() {
    const currentWidth = this.uiState.resize.chatSidebar;
    if (currentWidth > 0) {
      this.uiState.setChatSidebar(0); // Close the sidebar
    } else {
      this.uiState.setChatSidebar(375); // Open the sidebar to 400px (increased from 250px)
    }
  }

  handleInput(event) {
    this.textContent = event.target.value;
    
    // Auto-resize textarea
    const textarea = event.target as HTMLTextAreaElement;
    textarea.style.height = 'auto';
    textarea.style.height = Math.min(textarea.scrollHeight, 120) + 'px';
  }

  handleSendClick() {
    const inputElement = this.shadowRoot?.querySelector('#chatLLMInput') as HTMLTextAreaElement;
    if (inputElement) {
      const enterEvent = new KeyboardEvent('keydown', {
        key: 'Enter',
        code: 'Enter',
        keyCode: 13,
        which: 13,
        bubbles: true,
        cancelable: true
      });
      Object.defineProperty(enterEvent, 'target', {
        value: inputElement,
        enumerable: true
      });
      this.handleEnter(enterEvent);
    }
  }

  render() {
    return html`
      <style>
        .chat-container {
          display: flex;
          flex-direction: column;
          gap: 12px;
        }
        
        /* First Row - Text Input with Mic */
        .input-row {
          position: relative;
          width: 100%;
        }
        
        .text-input-wrapper {
          background: #25282D;
          border-radius: 16px;
          display: flex;
          align-items: flex-start;
          width: 100%;
          box-sizing: border-box;
          padding: 2px;
        }
        
        .text-input {
          flex: 1;
          background: transparent;
          border: none;
          outline: none;
          color: #FFFFFF;
          font-size: 14px;
          font-weight: 300;
          resize: none;
          min-height: 20px;
          max-height: 120px;
          overflow-y: auto;
          line-height: 1.4;
          font-family: inherit;
          padding-bottom:12px;
          padding-top:12px;
          scrollbar-width: none; /* Firefox */
          -ms-overflow-style: none; /* Internet Explorer 10+ */
        }
        
        .text-input:focus {
          outline: none;
          border: none;
          box-shadow: none;
        }
        
        .text-input::-webkit-scrollbar {
          display: none; /* WebKit */
        }
        
        .text-input::placeholder {
          color: rgba(142, 142, 147, 0.8);
          font-weight: 300;
        }
        
        .mic-button {
          background: transparent;
          border: none;
          color: rgba(142, 142, 147, 0.9);
          cursor: pointer;
          padding: 6px;
          border-radius: 6px;
          transition: all 0.2s ease;
          display: flex;
          align-items: center;
          justify-content: center;
          margin-left: 12px;
          margin-top: 6px;
          flex-shrink: 0;
        }
        
        .mic-button:hover {
          color: #FFFFFF;
          background: rgba(255, 255, 255, 0.1);
        }
        
        .mic-button.recording {
          color: #FF3B30;
        }
        
        .mic-button .material-symbols-outlined {
          font-size: 20px;
        }
        
        /* Second Row - Model Info and Send Button */
        .bottom-row {
          display: flex;
          align-items: center;
          justify-content: space-between;
          width: 100%;
        }
        
        .model-info {
          display: flex;
          align-items: center;
          gap: 8px;
          padding: 8px 16px;
          background: #515357;
          border-radius: 20px;
          border: 1px solid rgba(62, 62, 66, 0.6);
        }
        
        .meta-logo {
          width: 20px;
          height: 20px;
          opacity: 0.9;
          filter: brightness(0.8);
          object-fit: contain;
        }
        
        .model-name {
          color: #FFFFFF;
          font-size: 14px;
          font-weight: 400;
          letter-spacing: 0.2px;
        }
        
        .send-button {
          background: #E5E5E7;
          border: none;
          border-radius: 50%;
          width: 40px;
          height: 40px;
          display: flex;
          align-items: center;
          justify-content: center;
          cursor: pointer;
          transition: all 0.2s ease;
          flex-shrink: 0;
        }
        
        .send-button:hover {
          background: #D1D1D6;
          transform: scale(1.05);
        }
        
        .send-button:active {
          transform: scale(0.95);
        }
        
        .send-button .material-symbols-outlined {
          font-size: 18px;
          color: #1C1C1E;
        }
        
        /* Focus state for input */
        .text-input-wrapper:focus-within {
          /* Removed blue focus indicators */
        }
      </style>

      <div class="chat-container" style="background-color: #25282D; border-radius: 24px; padding: 12px; margin: 8px">
        <!-- First Row: Text Input with Mic -->
        <div class="input-row">
          <div class="text-input-wrapper">
            <textarea
              class="text-input"
              placeholder="${this.currentPlaceholder}"
              .value="${this.textContent}"
              id="chatLLMInput"
              @keydown=${this.handleEnter}
              @input=${this.handleInput}
              @click=${this.handleClickInput}
              rows="1"
            ></textarea>
            <button
              class="mic-button ${this.isRecording ? 'recording' : ''}"
              @click="${this.toggleRecording}"
              title="${this.isRecording ? "Stop recording" : "Start recording"}"
            >
              <span class="material-symbols-outlined">
                ${this.isRecording ? "stop_circle" : "mic"}
              </span>
            </button>
          </div>
        </div>

        <!-- Second Row: Model Info and Send Button -->
        <div class="bottom-row">
          <div class="model-info">
            <img 
              src="assets/meta.png" 
              alt="Meta" 
              class="meta-logo"
            />
            <span class="model-name">llama3.18 B</span>
          </div>
          
          <button class="send-button" @click="${this.handleSendClick}">
            <span class="material-symbols-outlined">
              arrow_upward
            </span>
          </button>
        </div>
      </div>
    `;
  }
} 