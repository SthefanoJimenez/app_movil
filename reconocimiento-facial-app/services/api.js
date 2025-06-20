import axios from 'axios';
import * as FileSystem from 'expo-file-system';

const API_URL = 'http://192.168.18.175:5000'; // Usa tu IP real

export const reconocerUsuario = async (foto) => {
  const formData = new FormData();
  formData.append('imagen', {
    uri: foto.uri,
    name: 'foto.jpg',
    type: 'image/jpeg',
  });

  const res = await axios.post(`${API_URL}/reconocer_usuario`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });

  return res.data;
};

export const registrarUsuario = async ({
  nombre,
  apellido,
  codigoUnico,
  email,
  requisitoriado,
  imagen,
}) => {
  const formData = new FormData();

  formData.append('nombre', nombre);
  formData.append('apellido', apellido);
  formData.append('codigo_unico', codigoUnico);
  formData.append('email', email);
  formData.append('requisitoriado', requisitoriado ? '1' : '0');

  formData.append('imagen', {
    uri: imagen.uri,
    name: 'registro.jpg',
    type: 'image/jpeg',
  });

  const res = await axios.post(`${API_URL}/registrar_usuario`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });

  return res.data;
};

