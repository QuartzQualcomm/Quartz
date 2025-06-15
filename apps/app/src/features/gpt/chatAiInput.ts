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

  constructor() {
    super();
    this.isEnter = false;
    this.isRecording = false;
    this.mediaRecorder = null;
    this.audioChunks = [];
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
    if (event.key === "Enter" && !this.isEnter) {
      this.isEnter = true;
      event.preventDefault();
      const command = (event.target.value || "").toLowerCase();
      if (command == "") {
        this.toast.show("Please enter a command", 2000);
        this.isEnter = false;
        return;
      } else {
        const timelineLatest = useTimelineStore.getState();
        const canvasLatestObject = document.querySelector("preview-canvas");
        const elementTimelineCanvasObject = document.querySelector(
          "element-timeline-canvas",
        );
        const AssetList = document.querySelector("asset-list")
        const context = {
          timeline: {
            cursor: timelineLatest.cursor / 1000,
            selected: elementTimelineCanvasObject.targetIdHistorical,
            selectedData:
              timelineLatest.timeline[
                elementTimelineCanvasObject.targetIdHistorical
              ],
          },
          preview: {
            selected: canvasLatestObject.activeElementId,
            selectedData:
              timelineLatest.timeline[canvasLatestObject.activeElementId],
          },
          files: AssetList.fileList || [],
          current_directory: AssetList.nowDirectory
        };
        // this.panelOpen();
        const chatLLMState = chatLLMStore.getState();
        chatLLMState.addList({
          from: "user",
          text: command,
          timestamp: new Date().toISOString(),
        });
        this.uiState = uiStore.getState();
        this.uiState.setThinking();

        try {
          if (window.electronAPI?.req?.quartz?.LLMResponse) {
            window.electronAPI.req.quartz
              .LLMResponse(command, context)
              .then((response) => {
                if (response.tool_name == "add_text") {
                  addTextElement(response.params);
                } else if (response.tool_name == "add_slide") {
                  addSlideElement(response.params);
                } else if (response.tool_name == "add_shape") {
                  addShapeElement(response.params);
                } 
                else if (response.tool_name == "add_file"){
                  addElement(response.params)
                }
                else if (response.tool_name == "video") {
                  console.log("Video response from LLM.");
                } else if (response.tool_name == "super_resolution") {
                  console.log(response.data);
                  renderNewImage(response.data.absolute_path, true);
                } else if (response.tool_name == "remove_background") {
                  console.log(response.data);
                  renderNewImage(response.data.absolute_path);
                } else if (response.tool_name == "potrait_effect") {
                  console.log(response.data);
                  renderNewImage(response.data.absolute_path);
                } else if (response.tool_name == "color_grading") {
                  console.log(response.data);
                  renderNewImage(response.data.absolute_path);
                } else if (response.tool_name == "export"){
                  console.log(response.data);
                  exportVideo(response.params);
                }
                else {
                  console.log("Unknown tool:", response.tool_name);
                }
                console.log("unset complete");
              })
              .catch((error) => {
                console.error("Error getting the response:", error);
                this.toast.show("Error getting the response", 2000);
              });
            // sleep for 1 second to allow the response to be processed
            setTimeout(() => {
              this.uiState = uiStore.getState();
              this.uiState.unsetThinking();
            }, 200);
          } else {
            console.error("IPC method 'quartz.LLMResponse' is not available");
            this.toast.show("LLMResponse functionality not available", 2000);
          }
          // Clear the input field after sending the command
          if (event.target) {
            (event.target as HTMLInputElement).value = "";
            this.textContent = "";
          }
        } catch (error) {
          console.error("Error processing the command:", error);
          this.toast.show("Error processing the command", 2000);
        }
      }

      setTimeout(() => {
        this.isEnter = false;
      }, 100);
    }
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
      this.uiState.setChatSidebar(250); // Open the sidebar to 250px
    }
  }

  handleInput(event) {
    this.textContent = event.target.value;
  }

  render() {
    return html`
      <style>
        .input-wrapper {
          flex-grow: 1;
          width:100%;
          display: flex;
          align-items: center;
          gap: 0.5rem;
          border-radius: 8px;
          background-color: #2C2C30;
          padding: 0.3rem 0.7rem;
          font-size: 0.85rem;
          box-shadow: 0px 2px 5px rgba(0, 0, 0, 0.3);
          border: 1px solid #3a3f44;
        }
        .chat-input {
          flex-grow: 1;
          width:100%;
          background-color: transparent;
          border: none;
          padding: 0;
          font-size: 0.85rem;
          color: #DCDCDC;
        }
        .send-button {
          background: transparent;
          border: none;
          color: #888888;
          font-size: 1.4rem;
          cursor: pointer;
          display: flex;
          align-items: center;
          justify-content: center;
          transition: color 0.2s ease;
        }
        .send-button:hover {
          color: #B0B0B0;
        }
      </style>
      <div class="input-wrapper">
        <input
          type="text"
          class="chat-input"
          placeholder="Ask me anything..."
          .value="${this.textContent}"
          id="chatLLMInput"
          @keydown="${this.handleEnter}"
          @input="${this.handleInput}"
          @click=${this.handleClickInput}
        />
        <button
          class="btn btn-sm p-0"
          @click="${this.toggleRecording}"
          title="${this.isRecording ? "Stop recording" : "Start recording"}"
        >
          <span
            class="material-symbols-outlined icon-sm ${this.isRecording
              ? "text-danger"
              : "text-secondary"}"
          >
            ${this.isRecording ? "stop_circle" : "mic"}
          </span>
        </button>
        <button class="send-button" @click="${this.handleEnter}">
          <span class="material-symbols-outlined">arrow_upward</span>
        </button>
      </div>
    `;
  }
} 