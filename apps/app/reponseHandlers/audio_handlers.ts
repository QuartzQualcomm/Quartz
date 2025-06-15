import { useTimelineStore } from "../src/states/timelineStore";
import { addTextElement } from "./text_handlers";

interface SRTSubtitle {
  index: number;
  startTime: number;
  endTime: number;
  text: string;
}

function parseSRT(srtContent: string): SRTSubtitle[] {
  const subtitles: SRTSubtitle[] = [];
  const blocks = srtContent.trim().split('\n\n');
  
  for (const block of blocks) {
    const lines = block.split('\n');
    if (lines.length < 3) continue;
    
    const index = parseInt(lines[0]);
    const timeLine = lines[1];
    const text = lines.slice(2).join(' ');
    
    const [startTimeStr, endTimeStr] = timeLine.split(' --> ');
    const startTime = timeToMilliseconds(startTimeStr);
    const endTime = timeToMilliseconds(endTimeStr);
    
    subtitles.push({
      index,
      startTime,
      endTime,
      text
    });
  }
  
  return subtitles;
}

function timeToMilliseconds(timeStr: string): number {
  const [time, ms] = timeStr.split(',');
  const [hours, minutes, seconds] = time.split(':').map(Number);
  return (hours * 3600 + minutes * 60 + seconds) * 1000 + parseInt(ms);
}

export async function addAutoCaption(absolute_path: string): Promise<boolean> {
  try {
    const previewCanvas = document.querySelector("preview-canvas");
    const ide = previewCanvas.activeElementId;
    
    // Read SRT file
    const response = await fetch(absolute_path);
    const srtContent = await response.text();
    
    // Parse SRT content
    const subtitles = parseSRT(srtContent);
    
    // Get timeline state
    let timelineState = useTimelineStore.getState();
    let timeline = timelineState.timeline;
    timeline[ide].localpath = absolute_path;
    timelineState.patchTimeline(timeline);
    
    // Add each subtitle as a text element
    for (const subtitle of subtitles) {
      await addTextElement({
        text: subtitle.text,
        startTime: subtitle.startTime,
        duration: subtitle.endTime - subtitle.startTime,
        locationX: 800, // Center of screen
        locationY: 600, // Bottom third of screen
        width: 1000,
        height: 200,
        textColor: "#ffffff",
        fontsize: 48,
        dataAlign: "center",
        backgroundEnable: true
      });
    }
    
    previewCanvas.drawCanvas();
    return true;
  } catch (error) {
    console.error("Error adding auto captions:", error);
    return false;
  }
}

