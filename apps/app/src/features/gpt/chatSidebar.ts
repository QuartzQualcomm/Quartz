import { LitElement, html } from "lit";
import { customElement, property } from "lit/decorators.js";
import { ITimelineStore, useTimelineStore } from "../../states/timelineStore";
import { IChatLLMPanelStore, chatLLMStore } from "../../states/chatLLM";
import { IUIStore, uiStore } from "../../states/uiStore";
// import "./aiInput"; // Removed as it's no longer directly used in chatSidebar
import "./chatAiInput"; // Import the new chat AI input component

@customElement("chat-sidebar")
export class ChatSidebar extends LitElement {
  constructor() {
    super();
  }

  @property()
  uiState: IUIStore = uiStore.getInitialState();

  @property()
  chatLLMState: IChatLLMPanelStore = chatLLMStore.getInitialState();

  @property()
  chatList = this.chatLLMState.list;

  @property()
  width = uiStore.getInitialState().resize.chatSidebar;

  thinking;

  createRenderRoot() {
    chatLLMStore.subscribe((state) => {
      this.chatList = state.list;
    });

    uiStore.subscribe((state) => {
      console.log("chat update -> thinking", state.thinking);
      this.thinking = state.thinking;
      // re render
      this.requestUpdate();
    });

    uiStore.subscribe((state) => {
      this.width = state.resize.chatSidebar;
      this.thinking = state.thinking;
      this.requestUpdate();
    });

    return this;
  }

  panelClose() {
    this.uiState.setChatSidebar(0);
  }

  clearChat() {
    chatLLMStore.setState({
      list: [
        {
          from: "agent",
          text: "Hello, I'm Quartz! I'm your personal local AI video editor powered by Qualcomm Snapdragon X. Start by giving me commands!",
          timestamp: new Date().toISOString(),
        }
      ]
    });
  }

  render() {
    const lists: any = [];

    for (let index = 0; index < this.chatList.length; index++) {
      const element = this.chatList[index];

      if (element.from == "user") {
        lists.push(html` <div class="message-container">
          <div class="message-header">
            <span class="material-symbols-outlined user-icon">account_circle</span>
            <span class="message-label">You</span>
          </div>
          <div class="message-content user-message">${element.text}</div>
        </div>`);
      } else if (element.from == "agent") {
        lists.push(html` <div class="message-container">
          <div class="message-content assistant-message">${element.text}</div>
        </div>`);
      }
    }

    return html`
      <style>
        .chat-top {
          border-bottom: 0.05rem #3a3f44 solid;
          height: 40px;
          display: flex;
          align-items: center;
          justify-content: space-between;
          padding: 0 1rem;
        }
        .chat-sidebar-container {
          min-width: ${this.width}px;
          width: ${this.width}px;
          z-index: 998;
          left: 0.75rem;
          position: relative;
          overflow-y: auto;
          padding-bottom: 5rem;
          display: flex;
          flex-direction: column;
          justify-content: space-between;
          font-size: 0.9rem;
        }
        .chat-box-container {
          flex-grow: 1;
          overflow-y: auto;
          padding: 1.5rem;
          margin-bottom: 6rem;
        }
        .sticky-input {
          position: sticky;
          bottom: 10;
          background-color: var(--bs-darker);
          padding: 0.75rem 1.3rem 2.2rem 0.5rem;
          border-top: none;
          align-items: center;
          justify-content: center;
          right:100;
        }
        .input-wrapper {
          flex-grow: 1;
          display: flex;
          align-items: center;
          gap: 0.2rem;
          border-radius: 8px;
          background-color: #2C2C30;
          padding: 0.5rem 0.5rem;
          font-size: 0.85rem;
          box-shadow: 0px 2px 5px rgba(0, 0, 0, 0.3);
          border: 1px solid #3a3f44;
        }
        .chat-input {
          flex-grow: 1;
          background-color: transparent;
          border: none;
          padding: 0;
          font-size: 0.85rem;
        }
        .message-container {
          margin-bottom: 1rem;
          padding: 0.45rem 0;
        }
        .message-header {
          display: flex;
          align-items: center;
          gap: 0.75rem;
          margin-bottom: 0.75rem;
        }
        .user-icon {
          color: #4A9EFF;
          font-size: 1.4rem;
        }
        .message-label {
          color: #888;
          font-size: 0.9rem;
        }
        .message-content {
          color: #DCDCDC;
          line-height: 1.6;
          white-space: pre-wrap;
          font-size: 0.95rem;
          padding: 0 0.5rem;
        }
        .user-message {
          color: #FFFFFF;
        }
        .assistant-message {
          color: #DCDCDC;
        }
        .new-chat-btn {
          background: transparent;
          border: none;
          color: #DCDCDC;
          padding: 0.25rem;
          cursor: pointer;
          display: flex;
          align-items: center;
          justify-content: center;
          transition: color 0.2s ease;
        }
        .new-chat-btn:hover {
          color: #4A9EFF;
        }
        .top-controls {
          display: flex;
          align-items: center;
          justify-content: flex-end;
          width: 100%;
        }
        .close-icon {
          color: #888;
          font-size: 1.1rem;
          cursor: pointer;
          padding: 0.25rem;
        }
        .close-icon:hover {
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

      <div
        style="min-width: ${this.width}px; width: ${this.width}px; z-index: 998; left: 0.75rem; position: relative; padding-bottom: 0;"
        class="${parseInt(this.width.toString()) <= 0 ? "d-none" : ""} h-100 bg-darker option-window chat-sidebar-container"
      >
        <div>
          <div class="chat-top">
            <span
              @click=${this.panelClose}
              class="material-symbols-outlined close-icon"
              >right_panel_close</span
            >
            <div class="top-controls">
              <button class="new-chat-btn" @click=${this.clearChat}>
                <span class="material-symbols-outlined icon-sm">add</span>
              </button>
            </div>
          </div>
          <div class="w-100 d-flex row gap-3 chat-box-container">${lists}</div>
        </div>

        <div class="d-flex justify-content-center align-items-center">
          ${this.thinking
            ? html`<span class="material-symbols-outlined icon-md text-secondary"
                >sync</span
              >
                <span class="text-secondary">Thinking...</span>`
            : ""}
        </div>

        <div class="sticky-input w-100">
          <chat-ai-input></chat-ai-input>
        </div>
      </div>
    `;
  }
}
