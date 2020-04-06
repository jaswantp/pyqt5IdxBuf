#shader vertex
#version 130

in vec2 position;
uniform mat4 u_mvp;

void main() {
    gl_Position = u_mvp * vec4(position.xy, 0.1f, 1.0f);
}

#shader fragment
#version 130

uniform vec4 u_color;

void main(){
    gl_FragColor = u_color;
}
