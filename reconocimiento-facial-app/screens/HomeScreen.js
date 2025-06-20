import React, { useState, useEffect } from 'react';
import { View, Text, Button, Image, StyleSheet, ActivityIndicator, Alert } from 'react-native';
import * as ImagePicker from 'expo-image-picker';
import { reconocerUsuario } from '../services/api';

const HomeScreen = () => {
  const [imagen, setImagen] = useState(null);
  const [resultado, setResultado] = useState(null);
  const [cargando, setCargando] = useState(false);

  // Solicitar permisos de cámara al cargar el componente
  useEffect(() => {
    (async () => {
      const { status } = await ImagePicker.requestCameraPermissionsAsync();
      if (status !== 'granted') {
        alert('Se requieren permisos de cámara para esta función.');
      }
    })();
  }, []);

  // Función para seleccionar imagen de galería
  const seleccionarImagen = async () => {
    const result = await ImagePicker.launchImageLibraryAsync({
      mediaTypes: ImagePicker.MediaTypeOptions.Images,
      quality: 1,
    });

    if (!result.canceled) {
      const foto = result.assets[0];
      setImagen(foto);
      enviarAlBackend(foto);
    }
  };

  // Función para tomar una foto con la cámara
  const tomarFoto = async () => {
    const result = await ImagePicker.launchCameraAsync({
      quality: 1,
      allowsEditing: false,
    });

    if (!result.canceled) {
      const foto = result.assets[0];
      setImagen(foto);
      enviarAlBackend(foto);
    }
  };

  // Función para enviar imagen al backend
  const enviarAlBackend = async (foto) => {
    try {
      setCargando(true);
      const res = await reconocerUsuario(foto);
      setResultado(res);
    } catch (err) {
      console.log('Error:', err);
      Alert.alert('Error', 'No se pudo conectar con el servidor.');
    } finally {
      setCargando(false);
    }
  };

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Reconocimiento Facial</Text>

      <Button title="Seleccionar Imagen de Galería" onPress={seleccionarImagen} />
      <View style={{ marginVertical: 10 }} />
      <Button title="Tomar Foto con Cámara" onPress={tomarFoto} />

      {cargando && <ActivityIndicator size="large" color="#007AFF" style={{ marginTop: 20 }} />}

      {resultado && (
        <View style={styles.resultado}>
          {resultado.mensaje ? (
            <Text style={styles.alerta}>{resultado.mensaje}</Text>
          ) : (
            <>
              <Text style={styles.texto}>
                Detectado: {resultado.nombre} {resultado.apellido}
              </Text>
              <Text>Código único: {resultado.codigo_unico}</Text>
              <Text>Similitud: {resultado.similitud_promedio}</Text>

              {resultado.alerta && (
                <Text style={styles.alerta}>
                  ⚠️ {resultado.mensaje_alerta}
                </Text>
              )}

              <Image
                source={{ uri: `http://192.168.18.175:5000/uploads/${resultado.imagen_referencia}` }}
                style={styles.imagen}
              />
            </>
          )}
        </View>
      )}
    </View>
  );
};

const styles = StyleSheet.create({
  container: { flex: 1, alignItems: 'center', paddingTop: 40 },
  title: { fontSize: 22, fontWeight: 'bold', marginBottom: 20 },
  texto: { fontSize: 18, marginVertical: 10 },
  alerta: { fontSize: 16, color: 'red', marginVertical: 10 },
  imagen: { width: 200, height: 200, marginTop: 10, borderRadius: 10 },
  resultado: { marginTop: 30, alignItems: 'center' },
});

export default HomeScreen;

