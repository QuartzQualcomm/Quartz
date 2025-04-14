import { parseBlurString } from "./blur";
import { Filter } from "./common";

const vertexShaderSource = `
  attribute vec2 a_position;
  attribute vec2 a_texCoord;
  varying vec2 v_texCoord;
  void main() {
    gl_Position = vec4(a_position, 0.0, 1.0);
    v_texCoord = a_texCoord;
  }
`;

const fragmentShaderSource = `
  precision mediump float;
  uniform sampler2D u_video;
  uniform float u_power;
  uniform vec2 u_mouse;
  varying vec2 v_texCoord;
  
  const int samples = 66;
  
  // 2D 회전 행렬 생성 함수
  mat2 rotate2d(float angle) {
    float s = sin(angle);
    float c = cos(angle);
    return mat2(c, -s, s, c);
  }
  
  // texture2D 호출을 감싸는 함수
  vec4 sample(vec2 uv) {
    return texture2D(u_video, uv);
  }
  
  // 2번 코드의 frag 함수 (u_power 값에 따라 효과 강도 조절)
  vec4 frag(vec2 uv) {
    float rotateDir = sin(length(uv - u_mouse) / (0.005 + u_power * 5.0));
    rotateDir = smoothstep(-0.3, 0.3, rotateDir) - 0.5;
    vec2 shiftDir = (uv - u_mouse) * vec2(-1.0, -1.0);
    vec4 color = vec4(0.0);
    for (int i = 0; i < samples; i++) {
      uv += float(i) / float(samples) * shiftDir * 0.01;
      uv -= u_mouse;
      uv *= rotate2d(rotateDir * u_power * float(i));
      uv += u_mouse;
      color += sample(uv) / float(samples + i);
    }
    return color * 1.5;
  }
  
  void main() {
    gl_FragColor = frag(v_texCoord);
  }
`;

export class RaidalBlur extends Filter<string> {
  positions = new Float32Array([-1, -1, 1, -1, -1, 1, -1, 1, 1, -1, 1, 1]);
  positionBuffer: WebGLBuffer | null = null;
  a_position: number;

  texCoordBuffer: WebGLBuffer | null = null;
  texCoords = new Float32Array([0, 0, 1, 0, 0, 1, 0, 1, 1, 0, 1, 1]);
  a_texCoord: number;

  u_video: WebGLUniformLocation | null;
  u_power: WebGLUniformLocation | null;
  u_mouse: WebGLUniformLocation | null;

  constructor(gl: WebGLRenderingContext) {
    super(gl, vertexShaderSource, fragmentShaderSource);

    this.positionBuffer = gl.createBuffer();
    this.a_position = gl.getAttribLocation(this.program, "a_position");

    this.texCoordBuffer = gl.createBuffer();
    this.a_texCoord = gl.getAttribLocation(this.program, "a_texCoord");

    this.u_video = gl.getUniformLocation(this.program, "u_video");
    this.u_power = gl.getUniformLocation(this.program, "u_power");
    this.u_mouse = gl.getUniformLocation(this.program, "u_mouse");
  }

  process(data: string, targetTexture: WebGLTexture): void {
    const gl = this.gl;

    gl.useProgram(this.program);
    gl.clearColor(0.0, 0.0, 0.0, 0.0);
    gl.clear(gl.COLOR_BUFFER_BIT);

    // Quad, 텍스쳐 좌표 바인딩
    {
      gl.bindBuffer(gl.ARRAY_BUFFER, this.positionBuffer);
      gl.bufferData(gl.ARRAY_BUFFER, this.positions, gl.STATIC_DRAW);
      gl.enableVertexAttribArray(this.a_position);
      gl.vertexAttribPointer(this.a_position, 2, gl.FLOAT, false, 0, 0);

      gl.bindBuffer(gl.ARRAY_BUFFER, this.texCoordBuffer);
      gl.bufferData(gl.ARRAY_BUFFER, this.texCoords, gl.STATIC_DRAW);
      gl.enableVertexAttribArray(this.a_texCoord);
      gl.vertexAttribPointer(this.a_texCoord, 2, gl.FLOAT, false, 0, 0);
    }

    // 유니폼 설정
    {
      gl.uniform1i(this.u_video, 0);

      const blurFactor = parseBlurString(data);
      gl.uniform1f(this.u_power, blurFactor.f);

      gl.uniform2fv(this.u_mouse, [0.5, 0.5]);
    }

    // 텍스처 바인딩
    {
      gl.activeTexture(gl.TEXTURE0);
      gl.bindTexture(gl.TEXTURE_2D, targetTexture);
      gl.uniform1i(this.u_video, 0);
    }

    gl.drawArrays(gl.TRIANGLES, 0, 6);
  }
}
